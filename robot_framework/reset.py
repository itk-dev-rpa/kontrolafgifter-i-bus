"""This module handles resetting the state of the computer so the robot can work with a clean slate."""

import os

import pyodbc
from itk_dev_shared_components.sap import multi_session, sap_login, sap_util, fmcacov
from python_serviceplatformen.authentication import KombitAccess
from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection

from robot_framework import config


def reset(orchestrator_connection: OrchestratorConnection) -> dict:
    """Clean up, close/kill all programs and start them again. """
    orchestrator_connection.log_trace("Resetting.")
    clean_up(orchestrator_connection)
    close_all(orchestrator_connection)
    kill_all(orchestrator_connection)
    return open_all(orchestrator_connection)


def clean_up(orchestrator_connection: OrchestratorConnection) -> None:
    """Do any cleanup needed to leave a blank slate."""
    orchestrator_connection.log_trace("Doing cleanup.")


def close_all(orchestrator_connection: OrchestratorConnection) -> None:
    """Gracefully close all applications used by the robot."""
    orchestrator_connection.log_trace("Closing all applications.")


def kill_all(orchestrator_connection: OrchestratorConnection) -> None:
    """Forcefully close all applications used by the robot."""
    orchestrator_connection.log_trace("Killing all applications.")
    os.system('taskkill /f /im winword.exe')
    sap_login.kill_sap()


def open_all(orchestrator_connection: OrchestratorConnection) -> dict:
    """Open all programs used by the robot."""
    orchestrator_connection.log_trace("Opening all applications.")

    sap_credentials = orchestrator_connection.get_credential(config.SAP_LOGIN)
    sap_login.login_using_cli(sap_credentials.username, sap_credentials.password)
    session = multi_session.get_all_sap_sessions()[0]
    connection = pyodbc.connect("Driver={ODBC Driver 17 for SQL Server};Server=FaellesSQL;Trusted_Connection=yes;")
    kombit_access = KombitAccess("55133018", "Certificate.pem")

    return {
        'session': session,
        'connection': connection,
        'kombit_access': kombit_access
    }
