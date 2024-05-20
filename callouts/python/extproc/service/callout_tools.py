"""Library of commonly used methods within a callout server."""

import argparse
import logging
from typing import Union, Optional

from envoy.config.core.v3.base_pb2 import HeaderValue
from envoy.config.core.v3.base_pb2 import HeaderValueOption
from envoy.service.ext_proc.v3.external_processor_pb2 import HeaderMutation
from envoy.service.ext_proc.v3.external_processor_pb2 import BodyResponse
from envoy.service.ext_proc.v3.external_processor_pb2 import HeadersResponse
from envoy.service.ext_proc.v3.external_processor_pb2 import ImmediateResponse
from envoy.type.v3.http_status_pb2 import StatusCode
import grpc


def _addr(value: str) -> tuple[str, int] | None:
  if not value:
    return None
  if ':' not in value:
    return None
  address_values = value.split(':')
  return (address_values[0], int(address_values[1]))


def add_command_line_args() -> argparse.ArgumentParser:
  """Adds command line args to pass into the CalloutServer constructor."""
  parser = argparse.ArgumentParser()
  parser.add_argument(
    '--secure_health_check',
    action='store_true',
    help='Run a HTTPS health check rather than an HTTP one.',
  )
  parser.add_argument(
    '--combined_health_check',
    action='store_true',
    help='Do not create a seperate health check server.',
  )
  parser.add_argument(
    '--address',
    type=_addr,
    help='Address for the server with format: "0.0.0.0:443"',
  )
  parser.add_argument(
    '--health_check_address',
    type=_addr,
    help=(
      'Health check address for the server with format: "0.0.0.0:80",'
      + ' if False, no health check will be run.'
    ),
  )
  parser.add_argument(
    '--insecure_address',
    type=_addr,
    help='Address for the insecure debug port with format: "0.0.0.0:443"',
  )

  parser.add_argument(
    '--port',
    type=int,
    help='Port of the server, uses default_ip as the ip unless --address'
    + ' is specified.',
  )
  parser.add_argument(
    '--health_check_port',
    type=int,
    help='Health check port of the server, uses default_ip as the ip'
    + ' unless --health_check_address is specified.',
  )
  parser.add_argument(
    '--insecure_port',
    type=int,
    help='Insecure debug port of the server, uses default_ip as the ip'
    + ' unless --insecure_address is specified.',
  )
  return parser


def add_header_mutation(
  add: list[tuple[str, str]] | None = None,
  remove: list[str] | None = None,
  clear_route_cache: bool = False,
  append_action: Optional[HeaderValueOption.HeaderAppendAction] = None,
) -> HeadersResponse:
  """Generate a HeadersResponse mutation for incoming callouts.

  Args:
    add: A list of tuples representing headers to add or replace.
    remove: List of header strings to remove from the callout.
    clear_route_cache: If true, will enable clear_route_cache on the generated
      HeadersResponse.
    append_action: Supported actions types for header append action.
  Returns:
    The constructed HeadersResponse object.
  """
  header_mutation = HeadersResponse()
  if add:
    for k, v in add:
      header_value_option = HeaderValueOption(
        header=HeaderValue(key=k, raw_value=bytes(v, 'utf-8'))
      )
      if append_action:
        header_value_option.append_action = append_action
      header_mutation.response.header_mutation.set_headers.append(
        header_value_option
      )
  if remove is not None:
    header_mutation.response.header_mutation.remove_headers.extend(remove)
  if clear_route_cache:
    header_mutation.response.clear_route_cache = True
  return header_mutation


def add_body_mutation(
  body: str | None = None,
  clear_body: bool = False,
  clear_route_cache: bool = False,
) -> BodyResponse:
  """Generate a BodyResponse for incoming callouts.

    If both body and clear_body are left as default, the incoming callout's
    body will not be modified.

  Args:
    body: Body text to replace the current body of the incomming callout.
    clear_body: If true, will clear the body of the incomming callout.
    clear_route_cache: If true, will enable clear_route_cache on the generated
      BodyResponse.

  Returns:
    The constructed BodyResponse object.
  """
  body_mutation = BodyResponse()
  if body:
    body_mutation.response.body_mutation.body = bytes(body, 'utf-8')
    if clear_body:
      logging.warning('body and clear_body are mutually exclusive.')
  else:
    body_mutation.response.body_mutation.clear_body = clear_body
  if clear_route_cache:
    body_mutation.response.clear_route_cache = True
  return body_mutation


def deny_callout(context, msg: str | None = None):
  """Deny a grpc callout and print an error message."""
  msg = msg or 'Callout content is invalid or not allowed'
  logging.warning(msg)
  context.abort(grpc.StatusCode.PERMISSION_DENIED, msg)


def header_immediate_response(
  code: StatusCode,
  headers: list[tuple[str, str]] | None = None,
  append_action: Union[HeaderValueOption.HeaderAppendAction, None] = None,
) -> ImmediateResponse:
  """Returns an ImmediateResponse for a header callout."""
  immediate_response = ImmediateResponse()
  immediate_response.status.code = code

  if headers:
    header_mutation = HeaderMutation()
    for k, v in headers:
      header_value_option = HeaderValueOption(
        header=HeaderValue(key=k, raw_value=bytes(v, 'utf-8'))
      )
      if append_action:
        header_value_option.append_action = append_action
      header_mutation.set_headers.append(header_value_option)

    immediate_response.headers.CopyFrom(header_mutation)
  return immediate_response
