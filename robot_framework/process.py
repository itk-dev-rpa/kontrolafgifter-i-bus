"""This module contains the main process of the robot."""

import os
import json
import csv
from io import BytesIO, TextIOWrapper

from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection
from OpenOrchestrator.database.queues import QueueStatus
from itk_dev_shared_components.sap import multi_session, fmcacov
from itk_dev_shared_components.misc import cpr_util
from itk_dev_shared_components.smtp import smtp_util
import pyodbc
from python_serviceplatformen.authentication import KombitAccess
from python_serviceplatformen import digital_post
import win32api

from robot_framework import config
from robot_framework.sub_process import sap_process, sql_process


def process(orchestrator_connection: OrchestratorConnection) -> None:
    """Do the primary process of the robot."""
    orchestrator_connection.log_trace("Running process.")

    session = multi_session.get_all_sap_sessions()[0]
    connection = pyodbc.connect("Driver={ODBC Driver 17 for SQL Server};Server=FaellesSQL;Trusted_Connection=yes;")
    kombit_access = KombitAccess("55133018", "Certificate.pem")  # TODO

    while queue_element := orchestrator_connection.get_next_queue_element(config.QUEUE_NAME):
        try:
            data = json.loads(queue_element.data)
            cpr = data['cpr']
            aftaler = data['aftaler']
            error = handle_task(session, connection, kombit_access, cpr, aftaler)
            orchestrator_connection.set_queue_element_status(queue_element.id, QueueStatus.IN_PROGRESS, message=error or "Brev(e) sendt")
            print(error)  # TODO
        except Exception as e:
            orchestrator_connection.set_queue_element_status(queue_element.id, QueueStatus.FAILED, message=str(e))
            raise
        if all(v < 100 for v in win32api.GetCursorPos()):
            print("Cursor in corner!")
            return

    send_status_mail(orchestrator_connection)


def handle_task(session, connection: pyodbc.Connection, kombit_access: KombitAccess, cpr: str, aftaler: list[str]) -> str | None:
    """Handles a task.

    Args:
        session: The SAP session object to use.
        connection: The database connection to use.
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


def send_status_mail(orchestrator_connection: OrchestratorConnection):
    """Fetch all 'in progress' queue elements from the queue,
    add their data and result to a csv file and send it by email,
    mark all queue elements as 'done'.

    Args:
        orchestrator_connection: The connection to Orchestrator.
    """
    queue_elements = orchestrator_connection.get_queue_elements(config.QUEUE_NAME, status=QueueStatus.IN_PROGRESS, limit=1000)
    if not queue_elements:
        return

    file = BytesIO()
    text_file = TextIOWrapper(file, newline='')

    csv_writer = csv.writer(text_file, delimiter=";")
    csv_writer.writerow(["CPR", "Aftaler", "Besked"])

    # Write a row for each aftale in the queue element
    for queue_element in queue_elements:
        data = json.loads(queue_element.data)
        message = queue_element.message or "Ingen besked. Muligvis en fejl."
        row = [data['cpr'], ", ".join(data['aftaler']), message]
        csv_writer.writerow(row)
    text_file.flush()

    smtp_util.send_email(
        receiver=json.loads(orchestrator_connection.process_arguments)['receivers'],
        sender=config.RESULT_SENDER,
        subject="Status på orienteringer om kontrolafgifter i bus",
        body="Hej\nHer er listen med behandlede sager vedr. unge under 18, som har fået kontrolafgifter i bus.\nVenlig hilsen\nRobotten",
        attachments=[smtp_util.EmailAttachment(file, "Resultat.csv")],
        smtp_port=config.SMTP_PORT,
        smtp_server=config.SMTP_SERVER
    )

    # Set all the queue elements as done
    for queue_element in queue_elements:
        orchestrator_connection.set_queue_element_status(queue_element.id, QueueStatus.DONE)


if __name__ == '__main__':
    conn_string = os.getenv("OpenOrchestratorConnString")
    crypto_key = os.getenv("OpenOrchestratorKey")
    oc = OrchestratorConnection("Kontrolafgifter test", conn_string, crypto_key, '{"receivers": "ghbm@aarhus.dk"}')
    process(oc)
