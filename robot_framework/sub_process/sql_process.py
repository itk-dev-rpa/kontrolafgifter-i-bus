
import pyodbc


def get_guardians(cpr: str, connection: pyodbc.Connection) -> tuple[str, ...]:
    """Get the cpr number of the guardians of the given cpr number.
    Look up in Borgerdim.

    Args:
        cpr: The cpr number of the person which guardians to find.
        connection: _description_

    Returns:
        A tuple of 0-2 cpr numbers.
    """
    cursor = connection.execute(
        """
        SELECT Foraeldremyndighed1, Foraeldremyndighed2 FROM DWH.dwh.BorgerDim
        WHERE CPR = ?
        AND Gyldig = 1
        """,
        cpr
    )

    if cursor.rowcount == 0:
        return tuple()

    return tuple(g for g in cursor.fetchone() if g)
