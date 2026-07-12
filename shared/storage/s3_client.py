from __future__ import annotations

import boto3

from shared.config.settings import get_settings


def get_s3_client():
    s = get_settings()
    kwargs = {"region_name": s.aws_region}
    if s.s3_endpoint_url:
        kwargs["endpoint_url"] = s.s3_endpoint_url
    return boto3.client("s3", **kwargs)
