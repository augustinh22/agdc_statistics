from mock import MagicMock

import numpy as np
from affine import Affine
from datacube.model import MetadataType
from datacube.utils.geometry import GeoBox, CRS
from datacube_stats.models import OutputProduct
from datacube_stats.output_drivers import GeotiffOutputDriver
from datacube_stats.statistics import NoneStat
from datetime import datetime
import pytest
import rasterio


@pytest.mark.parametrize("dtype,nodata", [
    ("int8", -5),
    ("uint8", 254),
    ("int16", -999),
    ('float32', np.nan),
    ('float64', np.nan),
])
def test_geotiff_outputs(tmpdir, dtype, nodata):
    size = 64
    chunk_size = int(size / 2)
    metadata_type = MetadataType({}, {})
    storage = {'chunking': {'x': chunk_size, 'y': chunk_size}}

    input_measurement_1 = {'name': 'sample_input_measurement_1',
                           'dtype': dtype,
                           'nodata': nodata,
                           'units': '1'}
    input_measurement_2 = {'name': 'sample_input_measurement_2',
                           'dtype': dtype,
                           'nodata': nodata,
                           'units': '1'}
    output_product = OutputProduct(metadata_type,
                                   input_measurements=[input_measurement_1, input_measurement_2],
                                   storage=storage,
                                   name='test_product',
                                   file_path_template='foo_bar.tif',
                                   stat_name='',
                                   statistic=NoneStat())
    task = MagicMock()
    task.geobox = GeoBox(size, size, Affine(1 / size, 0.0, 151.0, 0.0, -1 / size, -29.0), CRS('EPSG:4326'))
    task.output_products = {'sample_prod': output_product}
    task.tile_index = 0, 0
    task.time_period = datetime.now(), datetime.now()

    tile_index = (None, slice(0, chunk_size, None), slice(0, chunk_size, None))
    values = np.full((chunk_size, chunk_size), fill_value=7, dtype=dtype)

    #
    # Run the code we want to test
    #
    with GeotiffOutputDriver(task=task, storage=storage, output_path=str(tmpdir)) as output_driver:
        output_driver.write_data(prod_name='sample_prod', measurement_name='sample_input_measurement_1',
                                 tile_index=tile_index, values=values)

    # Check that it had the desired result
    output_filename = tmpdir / 'foo_bar.tif'
    assert output_filename.exists()
    with rasterio.open(str(output_filename)) as src:
        assert src.width == size
        assert src.height == size
        for i in range(1, 3):
            tags = src.tags(i)
            assert tags['name'] == 'sample_input_measurement_%s' % i
            assert 'end_date' in tags
            assert 'start_date' in tags
            assert 'source_product' in tags
