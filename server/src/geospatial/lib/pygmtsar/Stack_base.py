# ----------------------------------------------------------------------------
# PyGMTSAR
#
# This file is part of the PyGMTSAR project: https://github.com/mobigroup/gmtsar
#
# Copyright (c) 2021, Alexey Pechnikov
#
# Licensed under the BSD 3-Clause License (see LICENSE for details)
# ----------------------------------------------------------------------------
from .IO import IO
from .tqdm_joblib import tqdm_joblib
from .tqdm_dask import tqdm_dask


class Stack_base(tqdm_joblib, IO):

    def __repr__(self):
        return "Object %s %d items\n%r" % (
            self.__class__.__name__,
            len(self.df),
            self.df,
        )

    def to_dataframe(self):
        """
        Return a Pandas DataFrame for all Stack scenes.

        Returns
        -------
        pandas.DataFrame
            The DataFrame containing Stack scenes.

        Examples
        --------
        df = stack.to_dataframe()
        """
        return self.df

    def get_subswath_prefix(self, subswath, date=None):
        """
        Define stem and multistem using date
        """
        from datetime import datetime

        # use reference datetime if not defined
        if date is None:
            date = self.reference

        assert len(date) == 10, "ERROR: date format is not yyyy-mm-dd"

        return f"{date}_F{subswath}"

    def set_reference(self, reference):
        """
        Define reference scene for Stack object.

        Parameters
        ----------
        reference : str
            Date string representing the reference scene.

        Returns
        -------
        Stack
            Modified instance of the Stack class.

        Examples
        --------
        Set the reference scene to '2022-01-20':
        stack.set_reference('2022-01-20')
        """
        if reference is None:
            print(
                "NOTE: reference scene is None, Stack.set_reference() command is ignored"
            )
            return self
        assert reference in self.df.index, f"Reference scene not found: {reference}"
        self.reference = reference
        return self

    #     def get_reference(self, subswath=None):
    #         """
    #         Return dataframe reference record(s) for all or only selected subswath.
    #
    #         Parameters
    #         ----------
    #         subswath : str, optional
    #             The subswath to select. If None, all subswaths are considered. Default is None.
    #
    #         Returns
    #         -------
    #         pd.DataFrame
    #             The DataFrame containing reference records for the specified subswath.
    #         """
    #         df = self.df.loc[[self.reference]]
    #         if not subswath is None:
    #             df = df[df.subswath == subswath]
    #         assert len(df) > 0, f'Reference record for subswath {subswath} not found'
    #         return df

    # added workaround: when multi-sunswaths is called before merging return the first subswath record
    def get_reference(self, subswath=None):
        """
        Return dataframe reference record(s) for all or only selected subswath.

        Parameters
        ----------
        subswath : str, optional
            The subswath to select. If None, all subswaths are considered. Default is None.

        Returns
        -------
        pd.DataFrame
            The DataFrame containing reference records for the specified subswath.
        """
        df0 = self.df.loc[[self.reference]]

        # return all records
        if subswath is None:
            assert len(df0) > 0, f"Reference record for subswath {subswath} not found"
            return df0
        # filgter for subswath
        df = df0[df0.subswath == subswath]
        if len(df) == 0:
            df = df0[df0.subswath == int(str(subswath)[0])]
        assert len(df) > 0, f"Reference record for subswath {subswath} not found"
        return df

    def get_repeat(self, subswath=None, date=None):
        """
        Return dataframe repeat records (excluding reference) for selected subswath.

        Parameters
        ----------
        subswath : str, optional
            The subswath to select. If None, all subswaths are considered. Default is None.
        date : datetime, optional
            The date for which to return repeat records. If None, all dates are considered. Default is None.

        Returns
        -------
        pd.DataFrame
            The DataFrame containing repeat records for the specified subswath and date.
        """
        if date is None:
            idx = self.df.index.difference([self.reference])
        else:
            idx = [date]
        df = self.df.loc[idx]
        if subswath is None:
            return df
        return df[df.subswath == subswath]

    # enlist all the subswaths
    def get_subswaths(self):
        """
        Enlist all the subswaths.

        Returns
        -------
        np.array
            An array containing all unique subswaths.
        """
        import numpy as np

        # note: df.unique() returns unsorted values so it would be 21 instead of expected 12
        return np.unique(self.df.subswath)

    #     def get_subswath(self, subswath=None):
    #         """
    #         Check and return subswath or return an unique subswath to functions which work with a single subswath only.
    #
    #         Parameters
    #         ----------
    #         subswath : str, optional
    #             The subswath to check. If None, an unique subswath is returned. Default is None.
    #
    #         Returns
    #         -------
    #         str
    #             The checked or unique subswath.
    #         """
    #         # detect all the subswaths
    #         subswaths = self.get_subswaths()
    #         assert subswath is None or subswath in subswaths, f'ERROR: subswath {subswath} not found'
    #         if subswath is not None:
    #             return subswath
    #         assert len(subswaths)==1, f'ERROR: multiple subswaths {subswaths} found, merge them first using Stack.merge_parallel()'
    #         # define subswath
    #         return subswaths[0]

    def get_subswath(self, subswath=None):
        """
        Check and return subswath or return the first subswath to functions which work with a single subswath only.

        Parameters
        ----------
        subswath : str, optional
            The subswath to check. If None, an unique subswath is returned. Default is None.

        Returns
        -------
        str
            The checked or unique subswath.
        """
        # detect all the subswaths
        subswaths = self.get_subswaths()
        assert subswath is None or str(subswath) in str(
            subswaths
        ), f"ERROR: subswath {subswath} not found"
        if subswath is not None:
            return subswath
        # define subswath
        return int(str(subswaths[0])[0])

    def get_pairs(self, pairs, dates=False):
        """
        Get pairs as DataFrame and optionally dates array.

        Parameters
        ----------
        pairs : np.ndarray, optional
            An array of pairs. If None, all pairs are considered. Default is None.
        dates : bool, optional
            Whether to return dates array. Default is False.
        name : str, optional
            The name of the phase filter. Default is 'phasefilt'.

        Returns
        -------
        pd.DataFrame or tuple
            A DataFrame of pairs. If dates is True, also returns an array of dates.
        """
        import xarray as xr
        import pandas as pd
        import numpy as np
        from glob import glob

        if isinstance(pairs, pd.DataFrame):
            # workaround for baseline_pairs() output
            pairs = pairs.rename(columns={"ref_date": "ref", "rep_date": "rep"})
        elif isinstance(pairs, (xr.DataArray, xr.Dataset)):
            # pairs = pd.DataFrame({
            #                 'ref': pairs.coords['ref'].values,
            #                 'rep': pairs.coords['rep'].values
            #             })
            refs = pairs.coords["ref"].values
            reps = pairs.coords["rep"].values
            pairs = pd.DataFrame(
                {
                    "ref": refs if isinstance(refs, np.ndarray) else [refs],
                    "rep": reps if isinstance(reps, np.ndarray) else [reps],
                }
            )
        else:
            # Convert numpy array to DataFrame
            # in case of 1d array with 2 items convert to a single pair
            pairs_2d = [pairs] if np.asarray(pairs).shape == (2,) else pairs
            pairs = pd.DataFrame(pairs_2d, columns=["ref", "rep"])

        # Convert ref and rep columns to datetime format
        pairs["ref"] = pd.to_datetime(pairs["ref"])
        pairs["rep"] = pd.to_datetime(pairs["rep"])
        pairs["pair"] = [
            f"{ref} {rep}"
            for ref, rep in zip(pairs["ref"].dt.date, pairs["rep"].dt.date)
        ]
        # Calculate the duration in days and add it as a new column
        # pairs['duration'] = (pairs['rep'] - pairs['ref']).dt.days

        if dates:
            # pairs is DataFrame
            dates = np.unique(pairs[["ref", "rep"]].astype(str).values.flatten())
            return (pairs, dates)
        return pairs

    def get_pairs_matrix(self, pairs):
        """
        Create a matrix based on interferogram dates and pairs.

        Parameters
        ----------
        pairs : pandas.DataFrame or xarray.DataArray or xarray.Dataset
            DataFrame or DataArray containing interferogram date pairs.

        Returns
        -------
        numpy.ndarray
            A matrix with one row for every interferogram and one column for every date.
            Each element in the matrix is a float, with 1 indicating the start date,
            -1 indicating the end date, 0 if the date is covered by the corresponding
            interferogram timeline, and NaN otherwise.

        """
        import numpy as np
        import pandas as pd

        # also define image capture dates from interferogram date pairs
        pairs, dates = self.get_pairs(pairs, dates=True)
        pairs = pairs[["ref", "rep"]].astype(str).values

        # here are one row for every interferogram and one column for every date
        matrix = []
        for pair in pairs:
            # mrow = [date>=pair[0] and date<=pair[1] for date in dates]
            mrow = [
                (
                    -1
                    if date == pair[0]
                    else (
                        1
                        if date == pair[1]
                        else (0 if date > pair[0] and date < pair[1] else np.nan)
                    )
                )
                for date in dates
            ]
            matrix.append(mrow)
        matrix = np.stack(matrix).astype(np.float32)
        return matrix

    @staticmethod
    def phase_to_positive_range(phase):
        """
        Convert phase from the range [-pi, pi] to [0, 2pi].

        Parameters
        ----------
        phase : array_like
            Input phase values in the range [-pi, pi].

        Returns
        -------
        ndarray
            Phase values converted to the range [0, 2pi].

        Examples
        --------
        >>> phase_to_positive_range(np.array([-np.pi, -np.pi/2, np.pi, 2*-np.pi-1e-6, 2*-np.pi]))
        array([3.14159265, 4.71238898, 3.14159265, 6.28318431, 0.        ])
        """
        import numpy as np

        return (phase + 2 * np.pi) % (2 * np.pi)

    @staticmethod
    def phase_to_symmetric_range(phase):
        """
        Convert phase from the range [0, 2pi] to [-pi, pi].

        Parameters
        ----------
        phase : array_like
            Input phase values in the range [0, 2pi].

        Returns
        -------
        ndarray
            Phase values converted to the range [-pi, pi].

        Examples
        --------
        >>> phase_to_symmetric_range(np.array([0, np.pi, 3*np.pi/2, 2*np.pi]))
        array([ 0.        ,  3.14159265, -1.57079633,  0.        ])
        """
        import numpy as np

        return (phase + np.pi) % (2 * np.pi) - np.pi
