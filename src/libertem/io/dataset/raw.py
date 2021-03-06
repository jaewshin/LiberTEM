import numpy as np

from libertem.common import Slice, Shape
from .base import DataSet, Partition, DataTile, DataSetException, DataSetMeta


class RawFileReader(object):
    def __init__(self, meta, path, scan_size, detector_size_raw):
        self._path = path
        self._meta = meta
        self._scan_size = scan_size
        self._detector_size_raw = detector_size_raw

    def open_file(self):
        f = np.memmap(self._path, dtype=self._meta.dtype, mode='r',
                      shape=self._scan_size + self._detector_size_raw)
        ds_slice = Slice(origin=(0, 0, 0, 0), shape=self._meta.shape)
        return f[ds_slice.get()]  # crop off the two extra rows


class RawFileDataSet(DataSet):
    def __init__(self, path, scan_size, dtype, detector_size_raw, crop_detector_to, tileshape=None):
        self._path = path
        self._scan_size = tuple(scan_size)
        assert len(detector_size_raw) == 2
        self._detector_size_raw = tuple(detector_size_raw)  # example: (130, 128)
        self._detector_size = tuple(crop_detector_to)                # example: (128, 128)
        self._min_num_partitions = None  # FIXME
        if tileshape is None:
            # raw files are memory mapped -> works well with large tiles
            # (actual tiles are then as large as the partitions)
            tileshape = self._scan_size + self._detector_size
        self._tileshape = tuple(tileshape)
        self._sig_dims = len(self._detector_size)
        self._meta = DataSetMeta(
            shape=Shape(self._scan_size + self._detector_size, sig_dims=self._sig_dims),
            raw_shape=Shape(self._scan_size + self._detector_size, sig_dims=self._sig_dims),
            dtype=np.dtype(dtype)
        )

    def initialize(self):
        return self

    @property
    def dtype(self):
        return self._meta.dtype

    @property
    def shape(self):
        return self._meta.shape

    @property
    def raw_shape(self):
        return self._meta.raw_shape

    def get_reader(self):
        return RawFileReader(
            meta=self._meta,
            path=self._path,
            scan_size=self._scan_size,
            detector_size_raw=self._detector_size_raw,
        )

    def check_valid(self):
        try:
            reader = self.get_reader()
            reader.open_file()
            # TODO: check file size match
            # TODO: try to read from file?
            return True
        except (IOError, OSError, ValueError) as e:
            raise DataSetException("invalid dataset: %s" % e)

    def get_partitions(self):
        ds_slice = Slice(origin=(0, 0, 0, 0), shape=self.shape)
        partition_shape = self.partition_shape(
            datashape=self.shape,
            framesize=self._detector_size[0] * self._detector_size[1],
            dtype=self.dtype,
            target_size=256*1024*1024,
            min_num_partitions=self._min_num_partitions,
        )
        for pslice in ds_slice.subslices(partition_shape):
            # TODO: where should the tileshape be set? let the user choose for now
            yield RawFilePartition(
                tileshape=self._tileshape,
                meta=self._meta,
                reader=self.get_reader(),
                partition_slice=pslice,
            )

    def __repr__(self):
        return "<RawFileDataSet of %s shape=%s>" % (self.dtype, self.shape)


class RawFilePartition(Partition):
    def __init__(self, tileshape, reader, *args, **kwargs):
        self.tileshape = tileshape
        self.reader = reader
        super().__init__(*args, **kwargs)

    def get_tiles(self, crop_to=None, full_frames=False):
        if crop_to is not None:
            if crop_to.shape.sig != self.meta.shape.sig:
                raise DataSetException("RawFileDataSet only supports whole-frame crops for now")
        if full_frames:
            tileshape = (
                tuple(self.tileshape[:self.meta.shape.nav.dims]) + tuple(self.meta.shape.sig)
            )
        else:
            tileshape = self.tileshape
        f = self.reader.open_file()
        subslices = list(self.slice.subslices(shape=tileshape))
        for tile_slice in subslices:
            if crop_to is not None:
                intersection = tile_slice.intersection_with(crop_to)
                if intersection.is_null():
                    continue
            # NOTE: no need to re-use buffer, as there is none (mmap!)
            yield DataTile(
                data=f[tile_slice.get()],
                tile_slice=tile_slice
            )
