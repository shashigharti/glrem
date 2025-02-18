# ----------------------------------------------------------------------------
# PyGMTSAR
#
# This file is part of the PyGMTSAR project: https://github.com/mobigroup/gmtsar
#
# Copyright (c) 2021, Alexey Pechnikov
#
# Licensed under the BSD 3-Clause License (see LICENSE for details)
# ----------------------------------------------------------------------------
from .Stack_orbits import Stack_orbits
from .PRM import PRM
from .config import env


class Stack_reframe_gmtsar(Stack_orbits):

    def _ext_orb_s1a(self, subswath, date=None, debug=False):
        """
        Extracts orbital data for the Sentinel-1A satellite by running GMTSAR binary `ext_orb_s1a`.

        Parameters
        ----------
        subswath : int
            Subswath number to extract the orbital data from.
        stem : str
            Stem name used for file naming.
        date : str, optional
            Date for which to extract the orbital data. If not provided or if date is the reference,
            it will extract the orbital data for the reference. Defaults to None.
        debug : bool, optional
            If True, prints debug information. Defaults to False.

        Examples
        --------
        _ext_orb_s1a(1, 'stem_name', '2023-05-24', True)
        """
        import os
        import subprocess

        if date is None or date == self.reference:
            date == self.reference
            df = self.get_reference(subswath)
        else:
            df = self.get_repeat(subswath, date)

        orbit = os.path.relpath(df["orbitpath"].iloc[0], self.basedir)

        prefix = self.get_subswath_prefix(subswath, date)

        argv = ["ext_orb_s1a", f"{prefix}.PRM", orbit, prefix]
        if debug:
            print("DEBUG: argv", argv)
        p = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf8",
            cwd=self.basedir,
            env=env,
        )
        stdout_data, stderr_data = p.communicate()
        if len(stderr_data) > 0 and debug:
            print("DEBUG: ext_orb_s1a", stderr_data)
        if len(stdout_data) > 0 and debug:
            print("DEBUG: ext_orb_s1a", stdout_data)

        return

    # produce LED and PRM in basedir
    # when date=None work on reference scene
    def _make_s1a_tops(
        self,
        subswath,
        date=None,
        mode=0,
        rshift_fromfile=None,
        ashift_fromfile=None,
        debug=False,
    ):
        """
        Produces LED and PRM in the base directory by executing GMTSAR binary `make_s1a_tops`.

        Parameters
        ----------
        subswath : int
            Subswath number to process.
        date : str, optional
            Date for which to create the Sentinel-1A TOPS products. If not provided,
            it processes the reference image. Defaults to None.
        mode : int, optional
            Mode for `make_s1a_tops` script:
            0 - no SLC;
            1 - center SLC;
            2 - high SLCH and low SLCL;
            3 - output ramp phase.
            Defaults to 0.
        rshift_fromfile : str, optional
            Path to the file with range shift data. Defaults to None.
        ashift_fromfile : str, optional
            Path to the file with azimuth shift data. Defaults to None.
        debug : bool, optional
            If True, prints debug information. Defaults to False.

        Notes
        -----
        The function executes an external binary `make_s1a_tops`.
        Also, this function calls the `ext_orb_s1a` method internally.

        Examples
        --------
        _make_s1a_tops(1, '2023-05-24', 1, '/path/to/rshift.grd', '/path/to/ashift.grd', True)
        """
        import os
        import subprocess

        # or date == self.reference
        if date is None:
            date = self.reference
            df = self.get_reference(subswath)
            # for reference image mode should be 1
            mode = 1
        else:
            df = self.get_repeat(subswath, date)

        # TODO: use subswath
        xmlfile = os.path.relpath(df["metapath"].iloc[0], self.basedir)
        datafile = os.path.relpath(df["datapath"].iloc[0], self.basedir)
        prefix = self.get_subswath_prefix(subswath, date)

        argv = ["make_s1a_tops", xmlfile, datafile, prefix, str(mode)]
        if rshift_fromfile is not None:
            argv.append(rshift_fromfile)
        if ashift_fromfile is not None:
            argv.append(ashift_fromfile)
        if debug:
            print("DEBUG: argv", argv)
        p = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf8",
            cwd=self.basedir,
            env=env,
        )
        stdout_data, stderr_data = p.communicate()
        if len(stderr_data) > 0 and debug:
            print("DEBUG: make_s1a_tops", stderr_data)
        if len(stdout_data) > 0 and debug:
            print("DEBUG: make_s1a_tops", stdout_data)

        self._ext_orb_s1a(subswath, date, debug=debug)

        return

    def _assemble_tops(self, subswath, date, azi_1, azi_2, debug=False):
        """
        Assemble Sentinel-1 TOPS products for a given date and swath using GMTSAR binary `assemble_tops`.

        Parameters
        ----------
        subswath : int
            Subswath number to process.
        date : str
            Date for which to assemble the Sentinel-1A TOPS products.
        azi_1 : float
            Starting azimuth index. If set to zero, all bursts will be output.
        azi_2 : float
            Ending azimuth index. If set to zero, all bursts will be output.
        debug : bool, optional
            If True, prints debug information. Defaults to False.

        Examples
        --------
        _assemble_tops(1, '2023-05-24', 1685, 9732, True)
        """
        import numpy as np
        import os
        import subprocess

        df = self.get_repeat(subswath, date)
        # print ('scenes', len(df))

        # assemble_tops requires the same path to xml and tiff files
        datadirs = [os.path.split(path)[:-1] for path in df["datapath"]]
        metadirs = [os.path.split(path)[:-1] for path in df["metapath"]]
        if not datadirs == metadirs:
            # in case when the files placed in different directories we need to create symlinks for them
            datapaths = []
            for datapath, metapath in zip(df["datapath"], df["metapath"]):
                for filepath in [datapath, metapath]:
                    filename = os.path.split(filepath)[-1]
                    relname = os.path.join(self.basedir, filename)
                    if os.path.exists(relname) or os.path.islink(relname):
                        os.remove(relname)
                    os.symlink(os.path.relpath(filepath, self.basedir), relname)
                datapaths.append(os.path.splitext(filename)[0])
        else:
            datapaths = [
                os.path.relpath(path, self.basedir)[:-5] for path in df["datapath"]
            ]
        # print ('datapaths', datapaths)
        prefix = self.get_subswath_prefix(subswath, date)

        # round values and convert to strings
        azi_1 = np.round(azi_1).astype(int).astype(str)
        azi_2 = np.round(azi_2).astype(int).astype(str)

        argv = ["assemble_tops", azi_1, azi_2] + datapaths + [prefix]
        if debug:
            print("DEBUG: argv", argv)
        p = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf8",
            cwd=self.basedir,
            env=env,
        )
        stdout_data, stderr_data = p.communicate()
        if len(stderr_data) > 0 and debug:
            print("DEBUG: assemble_tops", stderr_data)
        if len(stdout_data) > 0 and debug:
            print("DEBUG: assemble_tops", stdout_data)

        return
