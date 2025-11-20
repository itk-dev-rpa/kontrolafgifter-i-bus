"""This module contains the main process of the robot."""

import os
import json

from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection
from OpenOrchestrator.database.queues import QueueStatus, QueueElement
from itk_dev_shared_components.sap import fmcacov
from itk_dev_shared_components.misc import cpr_util
import pyodbc
from python_serviceplatformen.authentication import KombitAccess
from python_serviceplatformen import digital_post

from robot_framework.sub_process import sap_process, sql_process


def process(orchestrator_connection: OrchestratorConnection, queue_element: QueueElement, session, connection: pyodbc.Connection, kombit_access: KombitAccess) -> None:
    """Do the primary process of the robot."""
    orchestrator_connection.log_trace("Running process.")

    data = json.loads(queue_element.data)
    cpr = data['cpr']
    aftaler = data['aftaler']
    error = handle_task(session, connection, kombit_access, cpr, aftaler)
    orchestrator_connection.set_queue_element_status(str(queue_element.id), QueueStatus.IN_PROGRESS, message=error or "Brev(e) sendt")


def handle_task(session, connection: pyodbc.Connection, kombit_access: KombitAccess, cpr: str, aftaler: list[str]) -> str | None:
    """Handles a task.

    Args:
        session: The SAP session object to use.
        connection: The database connection to use.
        kombit_access: Access token for Kombit.
        cpr: The cpr number of the person in question.
        aftaler: The aftaler of the person.

    Returns:
        An error message if any.
    """
    if cpr_util.get_age(cpr) >= 18:
        return "Person ikke under 18"

    guardians = sql_process.get_guardians(cpr, connection)
    if not guardians:
        return "Ingen værger fundet"

    # Check for Digital Post registrations
    receivers = []
    for g in guardians:
        if digital_post.is_registered(g, 'digitalpost', kombit_access):
            receivers.append(g)

    if not receivers:
        return "Ingen værger tilmeldt Digital Post."

    fmcacov.open_forretningspartner(session, cpr)

    for aftale in aftaler:
        error = sap_process.check_aftale(session, aftale)
        if error:
            return error

    letter_sent = False
    for receiver in receivers:
        letter_sent |= sap_process.send_letter(session, aftaler, receiver)

    if not letter_sent:
        return "Ingen værger tilmeldt Digital Post"

    return None


if __name__ == '__main__':
    conn_string = os.getenv("OpenOrchestratorConnString")
    crypto_key = os.getenv("OpenOrchestratorKey")
    oc = OrchestratorConnection("Kontrolafgifter test", conn_string, crypto_key, '{"receivers": "ghbm@aarhus.dk"}', "")
    process(oc)
