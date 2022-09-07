import boto3  # type: ignore
import boto3.session  # type: ignore


def use_localstack() -> None:
    """
    This function patches boto3 to use localstack
    """
    try:
        from localstack_client.patch import (  # type: ignore
            enable_local_endpoints,
            patch_expand_host_prefix,
        )

        enable_local_endpoints()
        patch_expand_host_prefix()
    except ImportError:
        from localstack_client import (  # type: ignore
            session as localstack_client_session,
        )

        localstack_session: localstack_client_session.Session = (
            localstack_client_session.Session()  # type: ignore
        )
        setattr(boto3, "client", localstack_session.client)
        setattr(boto3, "resource", localstack_session.resource)
        setattr(
            boto3.session,
            "Session",
            localstack_client_session.Session,  # type: ignore
        )
