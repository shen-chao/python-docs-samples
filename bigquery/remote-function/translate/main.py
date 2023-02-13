# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START bigquery_remote_function_translation]
import flask
import functions_framework
from google.api_core.retry import Retry
from google.cloud import translate

# Construct a Translation Client object
translate_client = translate.TranslationServiceClient()


# Register an HTTP function with the Functions Framework
@functions_framework.http
def handle_translation(request: flask.Request) -> flask.Response:
  """BigQuery remote function to translate input text.

  Args:
      request: HTTP request from BigQuery
      https://cloud.google.com/bigquery/docs/reference/standard-sql/remote-functions#input_format

  Returns:
      HTTP response to BigQuery
      https://cloud.google.com/bigquery/docs/reference/standard-sql/remote-functions#output_format
  """
  try:
    # Parse request data as JSON
    request_json = request.get_json()
    # Get the project of the query
    caller = request_json["caller"]
    project = extract_project_from_caller(caller)
    if project == None:
      return flask.make_response(
          flask.jsonify(
              {"errorMessage": f"project can't be extracted from {caller=}."}
          ),
          400,
      )
    # Get the target language code, default is "es"
    context = request_json["userDefinedContext"]
    target = context.get("target_language", "es")

    calls = request_json["calls"]
    translated = translate_text([call[0] for call in calls], project, target)

    return flask.jsonify({"replies": translated})
  except Exception as err:
    return flask.make_response(
        flask.jsonify({"errorMessage": f"Unexpected {err=}"}),
        400,
    )


def extract_project_from_caller(job: str) -> str:
  """Extract project id from full resource name of a BigQuery job.

  Args:
      job: full resource name of a BigQuery job, like
        "//bigquery.googleapi.com/projects/<project>/jobs/<job_id>"

  Returns:
      project id which is contained in the full resource name of the job.
  """
  path = job.split("/")
  return path[4] if len(path) > 4 else None


def translate_text(calls: list[str], project: str, target: str) -> list[str]:
  location = "us-central1"
  parent = f"projects/{project}/locations/{location}"
  # Call the Translation API, passing a list of values and the target language
  response = translate_client.translate_text(
      request={
          "parent": parent,
          "contents": calls,
          "target_language_code": target,
          "mime_type": "text/plain",
      },
      retry=Retry(),
  )
  # Convert the translated value to a list and return it
  return [translation.translated_text for translation in response.translations]


# [END bigquery_remote_function_translation]
