from os import path
import sys
import os
import re, fnmatch
import operator
import subprocess
import shutil
import zipfile

from libtbx.utils import Sorry
import libtbx.load_env

licence_text = """\
This CCTBX build make use of OpenBLAS and of its dependency libgfortran.
We reproduce below the licence of both.

OpenBLAS
--------
%(openblas_licence)s

libgfortran
-----------
Libgfortran is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public
License as published by the Free Software Foundation; either
version 3 of the License, or (at your option) any later version.

Libgfortran is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

Under Section 7 of GPL version 3, you are granted additional
permissions described in the GCC Runtime Library Exception, version
3.1, as published by the Free Software Foundation.

You should have received a copy of the GNU General Public License and
a copy of the GCC Runtime Library Exception along with this program;
see the files COPYING3 and COPYING.RUNTIME respectively.  If not, see
<http://www.gnu.org/licenses/>.  */
"""


def run(platform_info,
        build=False, stage=False, install=False, package=False,
        bits=None, procs_for_build=1):
  # Build a distro which can optimally run on any machine
  # with Intel or AMD processors
  if build:
    compilers = {}
    try:
      compilers['FC'] = subprocess.check_output(
        [os.environ['SHELL'], '-c', 'which gfortran']).strip()
    except subprocess.CalledProcessError:
      raise Sorry("No working gfortran. Please install one.\n\n"
                  "On MacOS, we recommend using MacPorts:\n"
                  "~> sudo port install gcc5\n"
                  "~> sudo port select --set gcc mp-gcc5\n\n"
                  "On Windows, please use the MinGW GUI.\n\n"
                  "On Linux, please use your platform package manager.\n")
    if platform_info.is_darwin():
      try:
        # we need clang to generate correct AVX code
        # (thanks to MacPorts portfile!)
        compilers['CC'] = subprocess.check_output(
          [os.environ['SHELL'], '-c', 'which clang']).strip()
      except subprocess.CalledProcessError:
        raise Sorry("Please install Apple Developer tools.")
    args = ['make', '-j%i' % procs_for_build,
            'USE_THREAD=1',
            'NUM_THREADS=16',
            'DYNAMIC_ARCH=1',
            'NO_STATIC=1']
    if bits:
      args.append('BINARY=%i' % bits)
    args.extend('%s=%s' % item for item in compilers.iteritems())
    cmd = ' '.join(args)
    subprocess.check_call(cmd, shell=True)

  # Stage it one level up from the current build directory
  stage_dir = path.join(abs(libtbx.env.build_path.dirname()), 'openblas')
  if stage:
    subprocess.check_call(['make',
                           'PREFIX=%s' % stage_dir,
                           'install'])

  # Install the headers and the DLL's in the CCTBX build directory
  # Note that we need to install the runtime library for GNU Fortran and GCC
  # We also install a README
  if install:
    openblas_inc = abs(libtbx.env.include_path / 'openblas')
    if path.isdir(openblas_inc): shutil.rmtree(openblas_inc)
    shutil.copytree(path.join(stage_dir, 'include'), openblas_inc)
    if platform_info.is_mingw():
      shutil.copy(path.join(stage_dir, 'bin', 'libopenblas.dll'),
                  abs(libtbx.env.lib_path))
      shutil.copy(path.join(stage_dir, 'lib', 'libopenblas.dll.a'),
                  path.join(abs(libtbx.env.lib_path), 'openblas.lib'))
      for dll in ('libgfortran-3.dll', 'libquadmath-0.dll',
                  'libgcc_s_dw2-1.dll'):
        shutil.copy(path.join('c:/mingw/bin', dll), abs(libtbx.env.lib_path))
    for f in ('COPYING3', 'COPYING.RUNTIME'):
      if platform_info.is_mingw():
        fmt = {'filename':f}
        fmt.update(platform_info)
        shutil.copy(
          'c:/mingw/share/doc/gcc/%(gcc_version)s/%(filename)s' % fmt,
          abs(libtbx.env.build_path))
    licences = {
      'openblas_licence': open('LICENSE').read(),
    }
    with open(path.join(abs(libtbx.env.build_path),
                        'openblas_licence'), 'w') as license:
      license.write(licence_text % licences)

  # Package the files added to the CCTBX build directory
  if package:
    arch = platform_info.arch_of_libopenblas()
    if platform_info.is_mingw():
      archive = zipfile.ZipFile(
        abs(libtbx.env.build_path.dirname() / ('openblas-windows-%s.zip' % arch)),
        mode="w")
      try:
        openblas_inc = libtbx.env.include_path / 'openblas'
        for p in ([openblas_inc] +
                  [openblas_inc / f for f in os.listdir(abs(openblas_inc))] +
                  [libtbx.env.lib_path / lib
                   for lib in ('libopenblas.dll', 'openblas.lib',
                               'libgfortran-3.dll', 'libquadmath-0.dll',
                               'libgcc_s_dw2-1.dll')] +
                  [libtbx.env.build_path / f
                   for f in ('copying3', 'copying.runtime',
                             'openblas_licence')]):
          archive.write(
            abs(p),
            arcname=path.relpath(abs(p), abs(libtbx.env.build_path)))
      finally:
        archive.close()


class platform_info(object):
  """ Information about architecture and compilers """

  supported_platforms = ('mingw32', 'mingw64',
                         'x86_64-apple-darwin15')

  darwin_mask = re.compile(r'^(\w+-apple-darwin\d+)')

  def __init__(self):
    self.c_compiler = 'gcc' if sys.platform != 'darwin' else 'clang'
    self.c_compiler_version = subprocess.check_output(
      [self.c_compiler, '-dumpversion']).strip()
    self.platform = subprocess.check_output(
      [self.c_compiler, '-dumpmachine']).strip()
    if sys.platform == 'darwin':
      m = self.darwin_mask.search(self.platform)
      self.platform = m.group(1)

  def check_support(self):
    if not reduce(
      operator.or_,
      (fnmatch.fnmatch(self.platform, p) for p in self.supported_platforms)):
      raise Sorry("The platform %s is not supported." % self.platform)

  def is_mingw(self):
    return self.platform.startswith('mingw')

  def is_darwin(self):
    return 'apple-darwin' in self.platform

  def is_linux(self):
    return 'linux' in self.platform

  def shared_library_suffix(self):
    return ('dll'   if self.is_mingw()  else
            'dylib' if self.is_darwin() else
            'so'    if self.is_linux()  else
            None)

  def arch_of_libopenblas(self):
    if self.is_mingw():
      ext = 'dll'
    elif self.is_darwin():
      ext = 'dylib'
    elif self.is_linux():
      ext = 'so'
    else:
      return None
    description = subprocess.check_output(
      ['file', abs(libtbx.env.lib_path /
                   ('libopenblas.%s' % self.shared_library_suffix()))])
    if '32-bit' in description:
      return '32'
    elif '64-bit' in description:
      return '64'
    else:
      return None


if __name__ == '__main__':
  import argparse
  import sys

  # Gather platform information and check we support it
  info = platform_info()
  info.check_support()

  # Parse arguments
  p = argparse.ArgumentParser(
    description=('Build OpenBLAS and prepare a package for distribution.\n'
                 'Please run this script from the top of an OpenBLAS working '
                 'directory, within MSYS shell on Windows. You will '
                 'need GNU C++ and Fortran compiler installed, using '
                 'MinGW to do so on Windows.')
  )
  features = ('build', 'stage', 'install', 'package')
  for arg in features:
    p.add_argument('--%s' % arg, dest=arg, action='store_true')
    p.add_argument('--no-%s' % arg, dest=arg, action='store_false')
  p.set_defaults(**dict((arg, False) for arg in features))
  p.add_argument('--bits', type=int, choices=(None, 32, 64), default=None,
                 help='Whether to build a 32- or 64-bit library '
                      '(None means that OpenBLAS build system shall decide)')
  p.add_argument('-j', dest='procs_for_build', type=int, default=1,
                 help='Number of cores to use for building')
  args = vars(p.parse_args())

  # Run
  try:
    run(platform_info=info, **args)
  except subprocess.CalledProcessError, e:
    print "\n*** Error %i ***\n" % e.returncode
    print "--- Reminder ---\n"
    print p.usage
