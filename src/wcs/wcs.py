import requests
import xmltodict
import time
# 127.0.0.1:7654/wcs?service=WCS&version=2.0.1&request=GetCoverage&coverageid=mod13q1&subset=time_id(0,0)&format=image/tiff&rangesubset=ndvi


class WCS(object):
    """
    WCS Module
    """

    url = None
    version = "2.0.1"
    coverages = []
    output = None

    def __init__(self, url="http://localhost:7654/wcs", output="/tmp"):
        self.url = url
        self.output = output

    def _build(self):
        return {"service": "WCS", "version": self.version}

    def _request(self, url, params=None):
        return requests.get(url, params=params)

    def get_capabilities(self):
        """
        It retrieves a Get Capabilities document
        """
        params = self._build()
        params["request"] = "GetCapabilities"
        req = self._request(self.url, params)

        json = xmltodict.parse(req.content)

        if not json.get("wcs:Capabilities"):
            raise RuntimeError("Its not a valid Capabilities Document")

        capabilities = json.get("wcs:Capabilities")

        contents = capabilities.get("wcs:Contents")

        if not contents:
            raise RuntimeError("This xml does not contains coverages")

        summaries = contents.get("wcs:CoverageSummary")

        if not summaries or not isinstance(summaries, list):
            raise RuntimeError("Invalid coverage summary")

        for summary in summaries:
            coverage_name = summary.get("wcs:CoverageId")
            metadata = {
                "id": coverage_name,
                "subtype": summary.get("wcs:CoverageSubtype")
            }
            self.coverages.append(metadata)

        return self.coverages

    def _read_coverage(self, description):
        fields = []
        data_record = description.get("gmlcov:rangeType", {}).get("swe:DataRecord", {})
        json_fields = data_record.get("swe:field", [])

        for json_field in json_fields:
            field = {
                "name": json_field.get("@name")
            }
            quantity = json_field.get("swe:Quantity")
            field["description"] = quantity.get("swe:Description")
            allowed_values = quantity.get("swe:constraint").get("swe:AllowedValues")
            minv, maxv = allowed_values.get("swe:interval", "").split(" ")

            field["interval"] = {"min": float(minv), "max": float(maxv)}

            fields.append(field)
        cov = filter(lambda ob: ob["id"] == description.get("@gml:id"), self.coverages)[0]
        cov["fields"] = fields

    @staticmethod
    def get_subsets(subsets):
        """
        Args:
            subsets (dict) - Subset elements to parse it
        Returns:
            str: A WCS 2.0 subset string representation
        """

        output = ""

        keys = subsets.keys()
        for i in range(0, len(keys)):
            key = keys[i]
            sb = subsets[key]

            if isinstance(sb, str):
                output += "subset={}({})".format(key, sb)
            elif isinstance(sb, list):
                output += "subset={}({},{})".format(key, sb[0], sb[1])
            else:
                raise StandardError("Subset must a list of values or just a value")

            if i + 1 < len(keys):
                output += "&"

        return output

    @staticmethod
    def get_range_subset(range_subset):
        """
        Args:
             range_subset (str|list)
        """
        if isinstance(range_subset, list):
            return ",".join(range_subset)
        if isinstance(range_subset, str):
            return range_subset
        raise StandardError("Invalid range subset")

    def describe_coverage(self, coverage_ids):
        """
        It retrieves a WCS describe coverage document

        Args:
             coverage_ids (str|list)
        """
        if isinstance(coverage_ids, list):
            pass
        elif isinstance(coverage_ids, str):
            pass
        else:
            raise StandardError("Coverage ID must be a string. Use delimiter ',' for more than one")

        coverages = ",".join(coverage_ids)

        params = self._build()
        params["request"] = "DescribeCoverage"
        params["coverageID"] = coverages

        req = self._request(self.url, params)

        json = xmltodict.parse(req.content)

        descriptions = json.get("wcs:CoverageDescriptions")
        if not descriptions:
            raise RuntimeError("Invalid Describe Coverage")

        descriptions = descriptions.get("wcs:CoverageDescription")
        if not descriptions:
            raise RuntimeError("Invalid Describe Coverage description")

        if isinstance(descriptions, list):
            for description in descriptions:
                self._read_coverage(description)
        else:
            self._read_coverage(descriptions)

        return self.coverages

    def get_coverage(self, coverage_id, subset=None, range_subset=None, **properties):
        """
        :param coverage_id
        :param subset
        :param range_subset
        :param properties
        """
        fmt = properties.get("format", "application/gml+xml")
        params = self._build()

        params["request"] = "GetCoverage"
        params["coverageID"] = coverage_id

        url = self.url
        if subset:
            if not isinstance(subset, dict):
                raise StandardError("Subset must be an object with axis name pointing to list with min and max values")
            url += "?" + WCS.get_subsets(subset)

        if range_subset:
            params["rangesubset"] = WCS.get_range_subset(range_subset)

        params["format"] = fmt

        req = self._request(url, params)

        if req.status_code != 200:
            raise StandardError("Failed to complete GetCoverage operation. Code {}".format(req.status_code))

        file_name = self.output + "/{0}-{1}.{2}".format(coverage_id, time.time(), "{}")
        if fmt == "application/gml+xml" or fmt == "application/xml":
            file_name = file_name.format("xml")
        elif fmt == "image/tiff":
            file_name = file_name.format("tiff")

        with open(file_name, "w") as f:
            f.write(req.content)
            f.close()

        return file_name
