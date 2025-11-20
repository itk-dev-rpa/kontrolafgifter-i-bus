"""To be run after the robot finishes."""
import csv
import json
from io import BytesIO, TextIOWrapper

from itk_dev_shared_components.smtp import smtp_util
from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection, QueueStatus

from robot_framework import config

def on_queue_empty(orchestrator_connection: OrchestratorConnection):
    """Run when the queue is empty."""
    orchestrator_connection.log_trace("Queue is empty.")
    send_status_mail(orchestrator_connection)

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
        orchestrator_connection.set_queue_element_status(str(queue_element.id), QueueStatus.DONE)