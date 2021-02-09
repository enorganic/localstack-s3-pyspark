import localstack_client.session as localstack_client_session  # type: ignore
import boto3  # type: ignore
import boto3.session  # type: ignore


def use_localstack() -> None:
    """
    This function patches boto3 to use localstack
    """
    localstack_session: localstack_client_session.Session = (  # type: ignore
        localstack_client_session.Session()  # type: ignore
    )
    setattr(boto3, "client", localstack_session.client)
    setattr(boto3, "resource", localstack_session.resource)
    setattr(
        boto3.session,
        "Session",
        localstack_client_session.Session,  # type: ignore
    )
