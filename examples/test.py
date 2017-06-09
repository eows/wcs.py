from __future__ import print_function
import sys
from wcs import WCS


if __name__ == "__main__":
    # Creating WCS object
    w = WCS()

    exit_code = 0

    try:
        # Downloading Coverage capabilities
        print("Retrieving capabilities ... ", end="")
        coverages = w.get_capabilities()
        print("done.")

        print("Coverages found -", ", ".join([cov["id"] for cov in coverages]))

        coverage_id = "mod13q1_tmp"
        print("Retrieving DescribeCoverage from {0} ... ".format(coverage_id), end="")
        d = w.describe_coverage([coverage_id]) # [coverage["id"] for coverage in c]
        print("done.")

        fmt = "application/xml"
        subset = {
          "time": "2002-02-18"
        }
        print("Downloading {} as {} format ... ".format(coverage_id, fmt), end="")
        f = w.get_coverage("mod13q1_tmp", range_subset="red", format=fmt)
        print("done.")

        print("File {}".format(f))
        sys.exit(0)
    except StandardError as e:
        print("Error: ", e.message)
        sys.exit(1)
