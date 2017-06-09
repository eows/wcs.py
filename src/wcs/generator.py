import gdal
import xmltodict
import numpy


driver = None


def initialize():
    gdal.AllRegister()

    global driver
    driver = gdal.GetDriverByName("GTiff")
    if not driver:
        raise StandardError("Could not retrieve GDAL GeoTIFF driver. Did you call initialize() before?")


def raise_if_is_none(value, err_msg):
    if value is None:
        raise StandardError(err_msg)


class Point(object):
    x = 0
    y = 0

    def __init__(self, x, y):
        self.x = x
        self.y = y


class Envelope(object):
    lower = None
    upper = None
    srs = None

    def __init__(self, point_min, point_max, srs=None, first_label=None, second_label=None):
        if not isinstance(point_min, Point) or not isinstance(point_max, Point):
            raise StandardError("Envelope must contains Point min and Point max object")

        self.lower = point_min
        self.upper = point_max
        self.srs = srs

    def lower_x(self):
        return self.lower.x

    def lower_y(self):
        return self.lower.y

    def upper_x(self):
        return self.upper.x

    def upper_y(self):
        return self.upper.y


class GMLToGeoTIFF(object):
    coverage_name = None
    envelope = None
    grid_envelope = None
    row_delimiter = ","
    data_delimiter = " "
    _raw = None
    attributes = None
    data = None

    def __init__(self, coverage_output):
        if isinstance(coverage_output, str):
            coverage_output = xmltodict.parse(coverage_output)

        self._raw = coverage_output

        grid_coverage = self._raw.get("gmlcov:GridCoverage")
        self.coverage_name = grid_coverage.get("@gml:id")

        raise_if_is_none(grid_coverage, "No grid coverage found")

        bounded_by = grid_coverage.get("gml:boundedBy")
        raise_if_is_none(bounded_by, "No bounded by element found")

        self._retrieve_envelope(bounded_by)

        domain_set = grid_coverage.get("gml:domainSet")
        raise_if_is_none(domain_set, "No domain set")

        self._retrieve_grid_envelope(domain_set)

        range_type = grid_coverage.get("gmlcov:rangeType")
        raise_if_is_none(range_type, "No range type")

        self._retrieve_attributes(range_type)

        range_set = grid_coverage.get("gml:rangeSet")
        raise_if_is_none(range_set, "No data found")

        self._retrieve_data(range_set)

    def _retrieve_envelope(self, bounded_by):
        envelope = bounded_by.get("gml:Envelope")
        if envelope is None or not isinstance(envelope, dict):
            raise StandardError("No gml:Envelope element found")

        labels = envelope.get("@axisLabels", "")
        raise_if_is_none(labels, "No axis labels provided")

        first_label, second_label, third_label = labels.split(" ")
        srs = envelope.get("@srsName")
        lower = envelope.get("gml:lowerCorner", "")
        upper = envelope.get("gml:upperCorner", "")

        x1, y1, t1 = lower.split(" ")
        x2, y2, t2 = upper.split(" ")
        point_min = Point(float(x1), float(y1))
        point_max = Point(float(x2), float(y2))
        self.envelope = Envelope(point_min, point_max, srs, first_label, second_label)

    def _retrieve_grid_envelope(self, domain_set):
        grid = domain_set.get("gml:Grid")
        raise_if_is_none(grid, "No domain set grid found")

        grid_envelope = grid.get("gml:limits", {}).get("gml:GridEnvelope")

        raise_if_is_none(grid_envelope, "No grid envelope found")

        low = grid_envelope.get("gml:low", "")
        high = grid_envelope.get("gml:high", "")

        x1, y1, t = low.split(" ")
        x2, y2, t = high.split(" ")
        point_min = Point(float(x1), float(y1))
        point_max = Point(float(x2), float(y2))
        self.grid_envelope = Envelope(point_min, point_max)

    def _retrieve_attributes(self, range_type):
        fields = range_type.get("swe:DataRecord")
        attributes = {}
        index = 0
        for key, field in fields.items():
            attribute = {"index": index}

            attributes[field.get("@name")] = attribute
            index += 1

        self.attributes = attributes

    def _retrieve_data(self, range_set):
        data_block = range_set.get("gml:DataBlock")
        raise_if_is_none(data_block, "No data block found")

        tuple_list = data_block.get("gml:tupleList")
        raise_if_is_none(tuple_list, "No tuple list")

        row_delimiter = tuple_list.get("@ts", self.row_delimiter)
        self.row_delimiter = row_delimiter

        data_delimiter = tuple_list.get("@cs", self.data_delimiter)
        self.data_delimiter = data_delimiter

        raw = tuple_list.get("#text", "")
        rows_data = raw.split(self.row_delimiter)

        data = {}
        for key, value in self.attributes.items():
            data[key] = []

        for row_data in rows_data:
            splited_fields = row_data.split(self.data_delimiter)

            for key, value in self.attributes.items():
                v = splited_fields[value["index"]]
                if not v:
                    continue
                data[key].append(int(v))

        self.data = data


    def save(self, filename=None):
        global driver
        if filename is None:
            filename = "/tmp/{0}.tiff".format(self.coverage_name)

        x = int(self.grid_envelope.upper_x() - self.grid_envelope.lower_x())
        y = int(self.grid_envelope.upper_y() - self.grid_envelope.lower_y())
        data_set = driver.Create(filename, x, y, len(self.attributes.keys()), gdal.GDT_Int16)
        # (GF_Write, 0, 0, x, y, buffer_, x, y, datatype_, 0, 0);
        raise_if_is_none(data_set, "Could not create GDAL dataset")
        band = data_set.GetRasterBand(1)

        # narray = numpy.reshape(self.data[self.attributes.keys()[0]], (y, x))
        narray = numpy.array(self.data[self.attributes.keys()[0]], numpy.int16).reshape(y, x)
        band.WriteArray(narray)

        data_set = None

