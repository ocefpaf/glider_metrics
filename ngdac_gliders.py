"""Compute glider metrics."""

import pandas as pd
from gliderpy.fetchers import GliderDataFetcher
from shapely.geometry import LineString


def ngdac_gliders(*, min_time, max_time, min_lat, max_lat, min_lon, max_lon):  # noqa: PLR0913
    """Loops over all datasets found within the bounding box and time-range,
    and returns a more accurate estimate for this metric.

    This approach can compute more refined metrics and other variables,
    like glider profiles and hurricane overlaps.
    """

    def _extra_info(info_df, attribute_name) -> str:
        """Get 'Attribute Name' 'Value' metadata."""
        return info_df.loc[info_df["Attribute Name"] == attribute_name]["Value"].squeeze()

    def _metadata(info_df) -> dict:
        """Build the metadata a specific dataset_id."""
        return {
            "wmo_id": _extra_info(info_df, attribute_name="wmo_id"),
            "time_coverage_start": _extra_info(
                info_df,
                attribute_name="time_coverage_start",
            ),
            "time_coverage_end": _extra_info(
                info_df,
                attribute_name="time_coverage_end",
            ),
            "glider": dataset_id.split("-")[0],
            "geospatial_lat_min": _extra_info(
                info_df,
                attribute_name="geospatial_lat_min",
            ),
            "geospatial_lat_max": _extra_info(
                info_df,
                attribute_name="geospatial_lat_max",
            ),
            "geospatial_lon_min": _extra_info(
                info_df,
                attribute_name="geospatial_lon_min",
            ),
            "geospatial_lon_max": _extra_info(
                info_df,
                attribute_name="geospatial_lon_max",
            ),
            "institution": _extra_info(info_df, attribute_name="institution"),
            "sea_name": _extra_info(info_df, attribute_name="sea_name"),
            "acknowledgment": _extra_info(
                info_df,
                attribute_name="acknowledgment",
            ),
        }

    def _computed_metadata(dataset_id) -> dict:
        """Download the minimum amount of data possible for the computed
        metadata.

        Note that we cannot get first and last b/c the profile_id is not a
        contiguous sequence.
        """
        glider_grab.fetcher.dataset_id = dataset_id
        glider_grab.fetcher.variables = [
            "profile_id",
            "latitude",
            "longitude",
            "time",
        ]
        df = glider_grab.to_pandas()
        df = df.sort_index()
        days = df.index[-1].ceil("D") - df.index[0].floor("D")
        return {
            "deployment_lat": df["latitude"].iloc[0],
            "deployment_lon": df["longitude"].iloc[0],
            "num_profiles": len(df),
            # Profiles are not unique! Cannot use this!!
            # "num_profiles": len(set(df['profile_id']))
            "days": days,
        }

    glider_grab = GliderDataFetcher()

    df = glider_grab.query(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        min_time=min_time,
        max_time=max_time,
        delayed=False,  # We do not want delayed gliders.
    )

    metadata = {}
    glider_grab.fetcher.variables = ["longitude", "latitude"]
    for _, row in list(df.iterrows()):
        dataset_id = row["Dataset ID"]

        glider_grab.fetcher.dataset_id = dataset_id
        track = glider_grab.fetcher.to_pandas(distinct=True)
        track = LineString(
            (lon, lat)
            for (lon, lat) in zip(
                track["longitude (degrees_east)"],
                track["latitude (degrees_north)"],
            )
        )

        info_url = row["info_url"].replace("html", "csv")
        info_df = pd.read_csv(info_url)
        info = _metadata(info_df)
        info.update(_computed_metadata(dataset_id=dataset_id))
        info.update({"track": track})
        metadata.update({dataset_id: info})
    return pd.DataFrame(metadata).T
