#!/usr/bin/env python
#
# FormatNexus.py
#
#  Copyright (C) 2013 Diamond Light Source
#
#  Author: James Parkhurst
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.

from __future__ import division

from dxtbx.format.FormatHDF5 import FormatHDF5
from dxtbx.model import Beam # import dependency
from dxtbx.model import Detector # import dependency
from dxtbx.model import Goniometer # import dependency
from dxtbx.model import Scan # import dependency
from dxtbx.format.nexus import NXmxReader
from dxtbx.format.nexus import BeamFactory
from dxtbx.format.nexus import DetectorFactory
from dxtbx.format.nexus import GoniometerFactory
from dxtbx.format.nexus import ScanFactory
from dxtbx.format.nexus import DataFactory
from dxtbx.format.nexus import MaskFactory

def find_entries(nx_file):
  '''
  Find NXmx entries

  '''
  if 'entry' in nx_file:
    entry = nx_file['entry']
    if 'NX_class' in entry.attrs.keys():
      if entry.attrs['NX_class'] == 'NXentry':
        if 'definition' not in entry.keys():
          return entry
  return None

def is_eiger_nearly_nexus_file(filename):
  '''
  A hacky function to check if this is an EIGER-flavoured nexus file

  '''
  import h5py

  # Get the file handle
  handle = h5py.File(filename, 'r')

  # Find the NXmx entries
  entry = find_entries(handle)
  if entry is not None:
    try:
      return 'Dectris Eiger' in entry['instrument']['detector']['description'].value
    except KeyError:
      pass
  return False


class EigerNXmxFixer(object):
  '''
  A hacky class to read an NXmx file

  '''
  def __init__(self, input_filename, memory_mapped_name):
    import h5py
    from scitbx import matrix

    # Copy the master file to the in memory handle
    handle_orig = h5py.File(input_filename, 'r')
    handle = h5py.File(name=memory_mapped_name, driver='core', backing_store=False, mode='w')
    handle_orig.copy('entry', handle)

    # Add some simple datasets
    def create_scalar(handle, path, dtype, value):
      dataset = handle.create_dataset(
        path, (), dtype=dtype)
      dataset[()] = value

    # Add NXmx definition
    create_scalar(
      handle['entry'],
      "definition",
      "S4",
      "NXmx")

    # Add saturation value
    try:
      create_scalar(
        handle['entry/instrument/detector'],
        "saturation_value",
        "int32",
        handle['/entry/instrument/detector/detectorSpecific/countrate_correction_count_cutoff'])
    except Exception:
      create_scalar(
        handle['entry/instrument/detector'],
        "saturation_value",
        "int32",
        handle['entry/instrument/detector/detectorSpecific/detectorModule_000/countrate_correction_count_cutoff'])

    # Add detector type
    create_scalar(
      handle['entry/instrument/detector'],
      "type",
      "S4",
      "PIXEL")

    # Move the beam
    # print "Copying /entry/instrument/beam to /entry/sample/beam"
    handle.copy(
      "/entry/instrument/beam",
      "/entry/sample/beam")

    # Create detector module
    module_path = '/entry/instrument/detector/module'
    # print "Creating detector module %s" % (module_path)
    group = handle.create_group(module_path)
    group.attrs['NX_class'] = "NXdetector_module"

    # Add a module index
    create_scalar(group, "module_index", "int64", 0)

    # Create detector data origin
    dataset = group.create_dataset("data_origin", (2,), dtype="int32")
    dataset[0] = 0
    dataset[1] = 0

    # Create detector data size
    dataset = group.create_dataset("data_size", (2,), dtype="int32")
    dataset[0] = handle_orig['/entry/data/data_000001'].shape[2]
    dataset[1] = handle_orig['/entry/data/data_000001'].shape[1]

    # cope with badly structured chunk information i.e. many more data
    # entries than there are in real life...
    delete = []
    for k in sorted(handle_orig['/entry/data'].iterkeys()):
      try:
        shape = handle_orig['/entry/data/%s' % k].shape
      except KeyError, e:
        delete.append('/entry/data/%s' % k)

    for d in delete:
      del(handle[d])

    # Add fast_pixel_size dataset
    # print "Using /entry/instrument/detector/geometry/orientation/value as fast/slow pixel directions"
    fast_axis = handle['/entry/instrument/detector/geometry/orientation/value'][0:3]
    slow_axis = handle['/entry/instrument/detector/geometry/orientation/value'][3:6]
    create_scalar(
      group,
      "fast_pixel_direction",
      "float32",
      handle['/entry/instrument/detector/x_pixel_size'].value)
    group['fast_pixel_direction'].attrs['transformation_type'] = 'translation'
    group['fast_pixel_direction'].attrs['vector'] = fast_axis
    group['fast_pixel_direction'].attrs['offset'] = 0
    group['fast_pixel_direction'].attrs['units'] = "m"
    group['fast_pixel_direction'].attrs['depends_on'] = '/entry/instrument/detector/transformations/translation'

    # Add slow_pixel_size dataset
    create_scalar(
      group,
      "slow_pixel_direction",
      "float32",
      handle['/entry/instrument/detector/y_pixel_size'].value)
    group['slow_pixel_direction'].attrs['transformation_type'] = 'translation'
    group['slow_pixel_direction'].attrs['vector'] = slow_axis
    group['slow_pixel_direction'].attrs['offset'] = 0
    group['slow_pixel_direction'].attrs['units'] = "m"
    group['slow_pixel_direction'].attrs['depends_on'] = '/entry/instrument/detector/transformations/translation'

    # Add module offset dataset
    # print "Set module offset to be zero relative to detector"
    create_scalar(
      group,
      "module_offset",
      "float32",
      0)
    group['module_offset'].attrs['transformation_type'] = 'translation'
    group['module_offset'].attrs['vector'] = (0, 0, 0)
    group['module_offset'].attrs['offset'] = 0
    group['module_offset'].attrs['units'] = "m"
    group['module_offset'].attrs['depends_on'] = '/entry/instrument/detector/transformations/translation'

    # Create detector depends_on
    depends_on = '/entry/instrument/detector/transformations/translation'
    create_scalar(
      handle['/entry/instrument/detector'],
      'depends_on',
      'S%d' % len(depends_on),
      depends_on)

    # Add detector position
    # print "Using /entry/instrument/detector/geometry/translation/distances as transformation"
    detector_offset_vector = matrix.col(handle['/entry/instrument/detector/geometry/translation/distances'][()])
    group = handle.create_group('/entry/instrument/detector/transformations')
    group.attrs['NX_class'] = 'NXtransformations'
    create_scalar(
      group,
      "translation",
      "float32",
      detector_offset_vector.length())
    group['translation'].attrs['transformation_type'] = 'translation'
    if detector_offset_vector.length() > 0:
      group['translation'].attrs['vector'] = detector_offset_vector.normalize()
    else:
      group['translation'].attrs['vector'] = detector_offset_vector
    group['translation'].attrs['offset'] = 0
    group['translation'].attrs['units'] = "m"
    group['translation'].attrs['depends_on'] = '.'

    # Create goniometer transformations if not found
    if '/entry/sample/transformations' not in handle:
      # print "Creating group /entry/sample/transformation"
      group = handle.create_group('/entry/sample/transformations')
      group.attrs['NX_class'] = 'NXtransformations'
    else:
      group = handle['/entry/sample/transformations']

    if 'omega' not in group:
      # print "Creating omega transformation:"
      # print " - making up rotation axis to be (1, 0, 0)"
      # print " - making up starting angle to be 0"
      # print " - using /entry/sample/goniometer/omega_range_average as oscillation range"
      # Get the number of images
      num_images = 0
      for name in sorted(handle['/entry/data'].iterkeys()):
        num_images += len(handle_orig['/entry/data/%s' % name])
      dataset = group.create_dataset('omega', (num_images,), dtype="float32")
      dataset.attrs['units'] = 'degree'
      dataset.attrs['transformation_type'] = 'rotation'
      dataset.attrs['vector'] = (1, 0, 0)
      dataset.attrs['offset'] = 0
      dataset.attrs['depends_on'] = '.'
      omega_range_average = handle['/entry/sample/goniometer/omega_range_average'][()]
      omega_range_average = int(omega_range_average * 100 + 0.5) / 100.0
      for i in range(num_images):
        angle = omega_range_average * i
        dataset[i] = angle
    else:
      dataset = group['omega']

    if 'depends_on' not in handle['/entry/sample']:
      # Create sample depends_on
      create_scalar(
        handle['/entry/sample'],
        'depends_on',
        'S%d' % len(dataset.name),
        str(dataset.name))

    # Change relative paths to absolute paths
    for name in handle['/entry/data'].iterkeys():
      del handle['entry/data'][name]
      filename = handle_orig['entry/data'][name].file.filename
      handle['entry/data'][name] = h5py.ExternalLink(filename, 'entry/data/data')
      handle['entry/data']["_filename_" + name] = filename # Store file namesa

    self.handle = handle

class FormatEigerNearlyNexus(FormatHDF5):

  def __init__(self, image_file):
    assert(self.understand(image_file))
    FormatHDF5.__init__(self, image_file)

  @staticmethod
  def understand(image_file):
    try:
      is_nexus = is_eiger_nearly_nexus_file(image_file)
    except IOError, e:
      return False
    return is_nexus

  def _start(self):

    # Read the file structure
    import uuid
    temp_file = "tmp_master_%s.nxs" % uuid.uuid1().hex
    fixer = EigerNXmxFixer(self._image_file, temp_file)
    reader = NXmxReader(handle=fixer.handle)

    # Only support 1 set of models at the moment
    assert len(reader.entries) == 1, \
      "Currently only supports 1 NXmx entry"
    assert len(reader.entries[0].data) == 1, \
      "Currently only supports 1 NXdata"
    assert len(reader.entries[0].instruments) == 1, \
      "Currently only supports 1 NXinstrument"
    assert len(reader.entries[0].samples) == 1, \
      "Currently only supports 1 NXsample"
    assert len(reader.entries[0].instruments[0].detectors) == 1, \
      "Currently only supports 1 NXdetector"
    assert len(reader.entries[0].instruments[0].detectors[0].modules) == 1, \
      "Currently only supports 1 NXdetector_module"
    assert len(reader.entries[0].samples[0].beams) == 1, \
      "Currently only supports 1 NXbeam"

    # Get the NXmx model objects
    entry = reader.entries[0]
    instrument = entry.instruments[0]
    detector = instrument.detectors[0]
    sample = entry.samples[0]
    beam = sample.beams[0]
    data = entry.data[0]

    # Construct the models
    self._beam_model = BeamFactory(beam).model
    self._detector_model = DetectorFactory(detector, self._beam_model).model
    self._goniometer_model = GoniometerFactory(sample).model
    self._scan_model = ScanFactory(sample, detector).model
    self._raw_data = DataFactory(data).model
    self._mask = (MaskFactory(detector).mask,)

  def _end(self):
    return

  def _goniometer(self):
    return self._goniometer_model

  def _detector(self):
    return self._detector_model

  def _beam(self):
    return self._beam_model

  def _scan(self):
    return self._scan_model

  def get_goniometer(self, index=None):
    return self._goniometer()

  def get_detector(self, index=None):
    return self._detector()

  def get_beam(self, index=None):
    return self._beam()

  def get_scan(self, index=None):
    if index is None:
      return self._scan()
    return self._scan()[index]

  def get_raw_data(self, index):
    return self._raw_data[index]

  def get_mask(self, index=None, goniometer_shadow_mask=False, goniometer=None):
    return self._mask

  def get_num_images(self):
    scan = self._scan()
    if isinstance(scan, list):
      return sum(s.get_num_images() for s in scan)
    return scan.get_num_images()

  def get_image_file(self, index=None):
    return self._image_file

  def get_detectorbase(self, index=None):
    raise RuntimeError('Overload!')

if __name__ == '__main__':
  import sys

  f = FormatEigerNearlyNexus(sys.argv[1])
  for i in range(10):
    print f.get_raw_data(i)
