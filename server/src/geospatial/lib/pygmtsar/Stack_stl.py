# ----------------------------------------------------------------------------
# PyGMTSAR
#
# This file is part of the PyGMTSAR project: https://github.com/mobigroup/gmtsar
#
# Copyright (c) 2023, Alexey Pechnikov
#
# Licensed under the BSD 3-Clause License (see LICENSE for details)
# ----------------------------------------------------------------------------
from .Stack_lstsq import Stack_lstsq
from .tqdm_dask import tqdm_dask


class Stack_stl(Stack_lstsq):

    @staticmethod
    def stl1d(ts, dt, dt_periodic, periods=52, robust=False):
        """
        Perform Seasonal-Trend decomposition using LOESS (STL) on the input time series data.

        The function performs the following steps:
        1. Check for NaN values in the input time series and return arrays filled with NaNs if found.
        2. Create an interpolation function using the input time series and corresponding time values.
        3. Interpolate the time series data for the periodic time values.
        4. Perform STL decomposition using the interpolated time series data.
        5. Return the trend, seasonal, and residual components of the decomposed time series.

        Parameters
        ----------
        ts : numpy.ndarray
            Input time series data.
        dt : numpy.ndarray
            Corresponding time values for the input time series data.
        dt_periodic : numpy.ndarray
            Periodic time values for interpolation.
        periods : int
            Number of periods for seasonal decomposition.
        robust : bool, optional
            Whether to use a robust fitting procedure for the STL decomposition (default is False).

        Returns
        -------
        numpy.ndarray
            Trend component of the decomposed time series.
        numpy.ndarray
            Seasonal component of the decomposed time series.
        numpy.ndarray
            Residual component of the decomposed time series.

        """
        import numpy as np
        from scipy.interpolate import interp1d
        from statsmodels.tsa.seasonal import STL

        # Check for NaNs in the input time series; this check is faster than letting STL handle NaNs
        if np.any(np.isnan(ts)):
            nodata = np.nan * np.zeros(dt_periodic.size)
            return nodata, nodata, nodata

        # Create an interpolation function for the input time series and time values
        interp_func = interp1d(
            dt, ts, kind="nearest", fill_value="extrapolate", assume_sorted=True
        )
        # Interpolate the time series data for the periodic time values
        ts = interp_func(dt_periodic)

        # Perform STL decomposition on the interpolated time series data
        stl = STL(ts, period=periods, robust=robust)
        res = stl.fit()

        return res.trend, res.seasonal, res.resid

    @staticmethod
    def stl_periodic(dates, freq="W"):
        import pandas as pd
        import xarray as xr
        import numpy as np

        # convert coordinate to valid dates
        dates = pd.to_datetime(dates)
        # original dates
        dt = dates.astype(np.int64)
        # Unify date intervals; using weekly intervals should be suitable for a mix of 6 and 12 days intervals
        dates_weekly = pd.date_range(dates[0], dates[-1], freq=freq)
        dt_weekly = xr.DataArray(dates_weekly, dims=["date"])
        dt_periodic = dt_weekly.astype(np.int64)
        return (dt, dt_periodic)

    # Aggregate data for varying frequencies (e.g., 12+ days for 6 days S1AB images interval)
    # Use frequency strings like '1W' for 1 week, '2W' for 2 weeks, '10d' for 10 days, '1M' for 1 month, etc.
    def stl(self, data, freq="W", periods=52, robust=False):
        """
        Perform Seasonal-Trend decomposition using LOESS (STL) on the input time series data in parallel.

        The function performs the following steps:
        1. Convert the 'date' coordinate to valid dates.
        2. Unify date intervals to a specified frequency (e.g., weekly) for a mix of time intervals.
        3. Apply the Stack.stl1d function in parallel using Dask.
        4. Rename the output date dimension to match the original irregular date dimension.
        5. Return the STL decomposition results as an xarray Dataset.

        Parameters
        ----------
        self : Stack
            Instance of the Stack class.
        data : xarray.DataArray
            Input time series data as an xarray DataArray.
        freq : str, optional
            Frequency string for unifying date intervals (default is 'W' for weekly).
        periods : int, optional
            Number of periods for seasonal decomposition (default is 52).
        robust : bool, optional
            Whether to use a slower robust fitting procedure for the STL decomposition (default is False).

        Returns
        -------
        xarray.Dataset or None
            An xarray Dataset containing the trend, seasonal, and residual components of the decomposed time series,
            or None if the results are saved to a file.

        See Also
        --------
        statsmodels.tsa.seasonal.STL : Seasonal-Trend decomposition using LOESS
            https://www.statsmodels.org/dev/generated/statsmodels.tsa.seasonal.STL.html
        """
        import xarray as xr
        import numpy as np
        import pandas as pd
        import dask

        # disable "distributed.utils_perf - WARNING - full garbage collections ..."
        try:
            from dask.distributed import utils_perf

            utils_perf.disable_gc_diagnosis()
        except ImportError:
            from distributed.gc import disable_gc_diagnosis

            disable_gc_diagnosis()

        assert data.dims[0] == "date", "The first data dimension should be date"

        if not "stack" in data.dims:
            chunks_z, chunks_y, chunks_x = (
                data.chunks if data.chunks is not None else np.inf,
                np.inf,
                np.inf,
            )
            if (
                np.max(chunks_y) > self.netcdf_chunksize
                or np.max(chunks_x) > self.netcdf_chunksize
            ):
                print(
                    f"Note: data chunk size ({np.max(chunks_y)}, {np.max(chunks_x)}) is too large for stack processing"
                )
                chunks_y = chunks_x = self.netcdf_chunksize // 2
                print(
                    f"Note: auto tune data chunk size to a half of NetCDF chunk: ({chunks_y}, {chunks_x})"
                )
            chunks = {"y": chunks_y, "x": chunks_x}
        else:
            chunks_z, chunks_stack = (
                data.chunks if data.chunks is not None else np.inf
            ), np.inf
            if np.max(chunks_stack) > self.chunksize1d:
                print(
                    f"Note: data chunk size ({np.max(chunks_stack)} is too large for stack processing"
                )
                # 1D chunk size can be defined straightforward
                chunks_stack = self.chunksize1d
                print(f"Note: auto tune data chunk size to 1D chunk: ({chunks_stack})")
            chunks = {"stack": chunks_stack}
        data = data.chunk(chunks)

        if isinstance(data, xr.DataArray):
            pass
        else:
            raise Exception(
                'Invalid input: The "data" parameter should be of type xarray.DataArray.'
            )

        dt, dt_periodic = self.stl_periodic(data.date, freq)

        def stl_block(ys, xs, stacks=None):
            # use external variables dt, dt_periodic, periods, robust
            if stacks is None:
                # 3D array
                data_block = (
                    data.isel(y=ys, x=xs)
                    .chunk(-1)
                    .compute(n_workers=1)
                    .values.transpose(1, 2, 0)
                )
            else:
                # 2D array
                data_block = (
                    data.isel(stack=stacks)
                    .chunk(-1)
                    .compute(n_workers=1)
                    .values.transpose(1, 0)
                )
            # Vectorize vec_lstsq
            # vec_stl = np.vectorize(lambda data: self.stl(data, dt, dt_periodic, periods, robust), signature='(n)->(3,m)')
            vec_stl = np.vectorize(
                lambda data: self.stl1d(data, dt, dt_periodic, periods, robust),
                signature="(n)->(m),(m),(m)",
            )
            # Apply vec_lstsq to data_block and revert the original dimensions order
            block = np.asarray(vec_stl(data_block))
            del vec_stl, data_block
            if stacks is None:
                return block.transpose(0, 3, 1, 2)
            return block.transpose(0, 2, 1)

        # split to chunks
        # use indices instead of the coordinate values to prevent the weird error raising occasionally:
        # "Reindexing only valid with uniquely valued Index objects"
        blocks_total = []
        if not "stack" in data.dims:
            # re-check the chunk sizes as it can be tunned above
            chunks_z, chunks_y, chunks_x = data.chunks
            ys_blocks = np.array_split(np.arange(data.y.size), np.cumsum(chunks_y)[:-1])
            xs_blocks = np.array_split(np.arange(data.x.size), np.cumsum(chunks_x)[:-1])

            for ys_block in ys_blocks:
                blocks = []
                for xs_block in xs_blocks:
                    block = dask.array.from_delayed(
                        dask.delayed(stl_block)(ys_block, xs_block),
                        shape=(3, len(dt_periodic), ys_block.size, xs_block.size),
                        dtype=np.float32,
                    )
                    blocks.append(block)
                    del block
                blocks_total.append(blocks)
                del blocks
            # specify 3D output coordinates
            coords = {
                "date": dt_periodic.astype("datetime64[ns]"),
                "y": data.y,
                "x": data.x,
            }
        else:
            chunks_z, chunks_stack = data.chunks
            stacks_blocks = np.array_split(
                np.arange(data["stack"].size), np.cumsum(chunks_stack)[:-1]
            )
            for stacks_block in stacks_blocks:
                block = dask.array.from_delayed(
                    dask.delayed(stl_block)(None, None, stacks_block),
                    shape=(3, len(dt_periodic), stacks_block.size),
                    dtype=np.float32,
                )
                blocks_total.append(block)
                del block
            # specify 2D output coordinates
            coords = {
                "date": dt_periodic.astype("datetime64[ns]"),
                "stack": data["stack"],
            }
        models = dask.array.block(blocks_total)
        del blocks_total

        # transform to separate variables
        # transform to separate variables variables returned from Stack.stl() function
        varnames = ["trend", "seasonal", "resid"]
        keys_vars = {
            varname: xr.DataArray(models[varidx], coords=coords)
            for (varidx, varname) in enumerate(varnames)
        }
        model = xr.Dataset({**keys_vars})
        del models

        return model
