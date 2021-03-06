
.. _installation:
.. contents:: Table of Contents

---------------------
Installation overview
---------------------

Periodically the most recent cctbx source code including all its
dependencies is automatically exported from the source code repositories
(SVN, CVS) and bundled into self-extracting files that are published
at:

  - http://cci.lbl.gov/cctbx_build/

This web page also provides self-extracting binary distributions for a
variety of platforms. It is most convenient to use these binary bundles
if possible. Installation is very simple and fast. The minimal
instructions are shown at the download page.

Source code bundles are also available. Under Unix, if Python 2.4
through 2.7 is pre-installed on the target platform, the smaller
``cctbx_bundle.selfx`` can be used. However, in general it will be
best to download the ``cctbx_python_*_bundle.selfx`` file because
the installation script will automatically install a recent Python
before proceeding with the installation of the cctbx modules.

The Unix bundles include a file ``cctbx_install_script.csh``.
This script is known to work with:

  - Linux: any gcc >= 3.2
  - Mac OS 10.4 or higher with Apple's compiler

Other Unix platforms will most likely require adjustments of the
build scripts.

The self-extracting source code bundle for Windows (``cctbx_bundle.exe``)
does not include an installation script.

-----------------------------------------
Manually building from sources under Unix
-----------------------------------------

Please note: **The following instructions are for developers!** The
self-extracting (.selfx) source bundles perform all the steps
automatically.

Building from sources requires Python 2.4 through 2.7 and a C++
compiler. If you like to use the most recent Python, it can be
installed in the following way::

  gunzip -c Python-2.7.2.tar.gz | tar xf -
  cd Python-2.7.2
  ./configure --prefix=/your/choice
  make
  make install

It may be convenient (but is not required) to add the directory
``/your/choice/bin`` to the command-line search ``PATH``, e.g. using
``csh``::

  set path=(/your/choice/bin $path)

Recent self-contained cctbx sources are available in the file
`cctbx_bundle.tar.gz <http://cci.lbl.gov/cctbx_build/results/last_published/cctbx_bundle.tar.gz>`_
published at the cctbx build page. To unpack this file in a new,
empty directory::

  tar zxf cctbx_bundle.tar.gz

This creates a subdirectory ``cctbx_sources``. The installation
procedure should be executed in another directory, e.g.::

  mkdir cctbx_build
  cd cctbx_build
  /your/choice/bin/python ../cctbx_sources/libtbx/configure.py mmtbx

The last command initializes the ``cctbx_build`` directory and creates a
file ``setpaths.csh`` (among others). This file must be used to
initialize a new shell or process with the cctbx settings::

  source setpaths.csh

There is also a ``setpaths.sh`` for ``bash`` users.

To compile enter::

  make

This will actually run the ``libtbx.scons`` command using all
available CPUs. You can also manually specify the number of CPUs to
use, for example::

  libtbx.scons -j 4

Note that ``libtbx.scons`` is just a thin wrapper around SCons_. The
`SCons documentation`_ applies without modification.

To run scripts with cctbx imports use the command::

  libtbx.python your_script.py

(You can also use ``scitbx.python``, ``cctbx.python``, ``iotbx.python``, etc.;
all these commands are equivalent.)

For example, to run some regression tests after the compilation is
finished enter::

  source setpaths_all.csh
  libtbx.python $SCITBX_DIST/run_tests.py
  libtbx.python $CCTBX_DIST/run_tests.py --Quick

The output should show many OK. A Python Traceback is an indicator
for problems.

-----------------------------------------------------------
Manually building from sources under Windows 2000 or higher
-----------------------------------------------------------

The cctbx installation requires Visual C++ 8.0 (Visual Studio .NET
2005) or higher.

To install Python under Windows it is best to use a binary
installer from the `Python download page <http://www.python.org/download/>`_.
The default choices presented by the installation wizard are usually fine.

Recent self-contained cctbx sources are available in the
self-extracting file
`cctbx_bundle.exe <http://cci.lbl.gov/cctbx_build/results/last_published/cctbx_bundle.exe>`_
published at the cctbx build page. To unpack this file in a new, empty
directory enter::

  cctbx_bundle.exe

This creates a subdirectory ``cctbx_sources``. The installation
procedure should be executed in another directory, e.g.::

  mkdir cctbx_build
  cd cctbx_build
  C:\python27\python.exe ..\cctbx_sources\libtbx\configure.py mmtbx

The last command initializes the ``cctbx_build`` directory and creates
a file ``setpaths.bat`` (among others). This file must be used to
initialize a new shell or process with the cctbx settings::

  setpaths.bat

To compile enter::

  libtbx.scons

On a machine with multiple CPUs enter::

  libtbx.scons -j N

where N is the number of CPUs available.

Note that ``libtbx.scons`` is just a thin wrapper around SCons_. The
`SCons documentation`_ applies without modification.

To run scripts with cctbx imports use the command::

  libtbx.python your_script.py

(You can also use ``scitbx.python``, ``cctbx.python``, ``iotbx.python``, etc.;
all these commands are equivalent.)

For example, to run some regression tests after the compilation is
finished enter::

  setpaths_all.bat
  libtbx.python %SCITBX_DIST%\run_tests.py
  libtbx.python %CCTBX_DIST%\run_tests.py --Quick

The output should show many OK. A Python Traceback is an indicator
for problems.

------------------------------
Using the cctbx SVN repository
------------------------------

To participate in the development of the cctbx project, or to
get easy access to the most recent changes, it may be useful
to checkout the cctbx project directly from the git repository
maintained at Github_. An easy way to get started is::

  wget https://raw.githubusercontent.com/cctbx/cctbx_project/master/libtbx/development/cctbx_svn_getting_started.csh
  ./cctbx_svn_getting_started.csh

The script will create a ``sources`` directory with a ``cctbx_project``
repository checked out from Github, and all other
third-party sources (e.g. boost, scons) taken from the latest nightly
cctbx build.

To configure a new build using the ``sources`` directory::

  mkdir build
  cd build
  /your/choice/bin/python ../sources/cctbx_project/libtbx/configure.py mmtbx
  source setpaths.csh
  make

It is also possible to replace the ``sources/boost`` directory with
a working copy of the `boost SVN tree`_ . However, in practice
it sometimes happens that a ``svn update`` of the boost tree
leads to compilation errors on some platforms. In most cases
it will be best to use the boost sources obtained with the
``cctbx_svn_getting_started.csh`` script.

Back_

.. _Back: introduction.html

.. _SCons: http://www.scons.org/
.. _`SCons documentation`: http://www.scons.org/doc/HTML/scons-man.html
.. _Boost: http://www.boost.org/
.. _`boost SVN tree`: http://svn.boost.org/trac/boost/wiki/BoostSubversion
.. _CCP4: http://www.ccp4.ac.uk/
.. _Github: https://github.com/cctbx/
