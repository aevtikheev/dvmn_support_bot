"""Common functions to work with Dialogflow API."""

import logging
from dataclasses import dataclass

from google.cloud import dialogflow
from google.api_core.exceptions import GoogleAPIError
from dataclasses_json import dataclass_json

from env_settings import env_settings


logger = logging.getLogger()


@dataclass_json
@dataclass
class GoogleCreds:
    """Google credentials for Dialogflow."""
    type: str
    project_id: str
    private_key_id: str
    private_key: str
    client_email: str
    client_id: str
    auth_uri: str
    token_uri: str
    auth_provider_x509_cert_url: str
    client_x509_cert_url: str


@dataclass
class Response:
    """Response from a Dialogflow API."""
    text: str
    is_fallback: bool


def _get_google_creds() -> GoogleCreds:
    """Get Google application credentials from the GOOGLE_APPLICATION_CREDENTIALS file."""
    with open(env_settings.google_app_creds_file, 'r') as google_creds_file:
        return GoogleCreds.from_json(google_creds_file.read())


def get_response(session_id: str, text: str, language_code: str) -> Response:
    """Returns the result of detect intent with text as input."""
    google_creds = _get_google_creds()

    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(google_creds.project_id, session_id)

    logger.info(f'Session {session_id} with language code {language_code}')

    text_input = dialogflow.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)
    response = session_client.detect_intent(request={'session': session, 'query_input': query_input})

    logger.info(
        f'Query text: {response.query_result.query_text}, '
        f'Detected intent: {response.query_result.intent.display_name}, '
        f'Confidence: {response.query_result.intent_detection_confidence}, '
        f'Fulfillment text: {response.query_result.fulfillment_text}'
    )

    return Response(
        text=response.query_result.fulfillment_text,
        is_fallback=response.query_result.intent.is_fallback
    )


def train_agent(intents: list) -> None:
    """
    Trains Dialogflow with provided intents.

    :param intents: A list with intents in JSON format. The example of an intent:
        {
            "display_name": "Name of an intent",
            "messages": [{
                "text": {
                    "text": ["О, Response text"]
                }
            }],
            "training_phrases": [
                {
                    "parts": [{"text": "First training phrase"}]
                },
                ...
            ]
        }
    """
    google_creds = _get_google_creds()

    intents_client = dialogflow.IntentsClient()
    agents_client = dialogflow.AgentsClient()

    for intent in intents:
        try:
            intents_client.create_intent(parent=f'projects/{google_creds.project_id}/agent', intent=intent)
            logger.info(f'Intent "{intent["display_name"]}" created')
            agents_client.train_agent(parent=f'projects/{google_creds.project_id}')
            logger.info(f'Intent "{intent["display_name"]}" trained')
        except GoogleAPIError as exception:
            logger.error(f'Intent "{intent["display_name"]}" was not created')
            logger.exception(exception)
