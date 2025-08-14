from _ctypes import COMError


import uiautomation
from itk_dev_shared_components.sap import gridview_util, tree_util
import win32clipboard


def check_aftale(session, aftale: str) -> str | None:
    """Check if a aftale is still on the list and not locked.

    Args:
        session: The SAP session.
        aftale: The aftale number.

    Returns:
        An error message if any
    """

    # Check if aftale still exists in postliste
    postliste = session.findById("wnd[0]/usr/tabsDATA_DISP/tabpDATA_DISP_FC1/ssubDATA_DISP_SCA:RFMCA_COV:0202/cntlRFMCA_COV_0100_CONT5/shellcont/shell")
    row = gridview_util.find_row_index_by_value(postliste, column="VTREF", value=aftale)
    if row == -1:
        return f"Aftale ikke i postliste: {aftale}"

    # Check rykkerspærre in aftale tree
    tree = session.findById("wnd[0]/shellcont/shell")
    node_key = tree_util.get_node_key_by_text(tree, text=aftale)

    # Check for padlock icon
    if tree.getItemType(node_key, "5_LOCKR") != 0:
        return f"Rykkerspærre på aftale: {aftale}"

    return None


def send_letter(session, aftaler: list[str], receiver_cpr: str) -> bool:
    session.findById("wnd[0]/tbar[1]/btn[25]").press()

    # Select letter template
    letter_select = session.findById("wnd[1]/usr/cntlTOOLBAR_CONTAINER/shellcont/shell")
    row = gridview_util.find_row_index_by_value(letter_select, "FIELD", "Individuel rykkerskrivelse")
    letter_select.click(row, "FIELD")
    session.findById("wnd[0]/usr/cmbZHJM0011_TEMPLAT-ID").key = "7510898750"

    # Filter on aftaler
    session.findById("wnd[0]/usr/subSEARCH1:ZDKD0052_CREATE_IDENT_LETTERS:0322/cntlALV_0320/shellcont/shell").setCurrentCell(-1, "VTREF")
    session.findById("wnd[0]/usr/subSEARCH1:ZDKD0052_CREATE_IDENT_LETTERS:0322/cntlALV_0320/shellcont/shell").selectColumn("VTREF")
    session.findById("wnd[0]/usr/subSEARCH1:ZDKD0052_CREATE_IDENT_LETTERS:0322/cntlALV_0320/shellcont/shell").contextMenu()
    session.findById("wnd[0]/usr/subSEARCH1:ZDKD0052_CREATE_IDENT_LETTERS:0322/cntlALV_0320/shellcont/shell").selectContextMenuItem("&FILTER")
    session.findById("wnd[1]/usr/ssub%_SUBSCREEN_FREESEL:SAPLSSEL:1105/btn%_%%DYN001_%_APP_%-VALU_PUSH").press()
    _set_clipboard("\r\n".join(aftaler))
    session.findById("wnd[2]/tbar[0]/btn[24]").press()
    session.findById("wnd[2]/tbar[0]/btn[8]").press()
    session.findById("wnd[1]/tbar[0]/btn[0]").press()

    # Insert letter data
    session.findById("wnd[0]/usr/subSEARCH1:ZDKD0052_CREATE_IDENT_LETTERS:0322/subSUB_0320:ZDKD0052_CREATE_IDENT_LETTERS:0323/cmbTFK047ET-CHGID").key = " "
    session.findById("wnd[0]/usr/subSEARCH1:ZDKD0052_CREATE_IDENT_LETTERS:0322/subSUB_0320:ZDKD0052_CREATE_IDENT_LETTERS:0323/cmbTFK047ST-MANSP").key = "B"
    session.findById("wnd[0]/usr/subSEARCH1:ZDKD0052_CREATE_IDENT_LETTERS:0322/subSUB_0320:ZDKD0052_CREATE_IDENT_LETTERS:0323/txtFKKRACT-MSPOP_DAYS").text = "19"

    # Select all and generate letter
    session.findById("wnd[0]/usr/subSEARCH1:ZDKD0052_CREATE_IDENT_LETTERS:0322/cntlALV_0320/shellcont/shell").selectAll()
    session.findById("wnd[0]/usr/btnPRINT_BUTTON").press()

    # Enter title and receiver
    session.findById("wnd[1]/usr/radGS_SCREEN_600-RAD2").select()
    session.findById("wnd[1]/usr/subSUB2:SAPLZDKD_KOR_MERGE_LETTERS:0602/txtGS_ODA_600-TITLE").text = "Orientering til forældre"
    session.findById("wnd[1]/usr/subSUB2:SAPLZDKD_KOR_MERGE_LETTERS:0602/ctxtGS_ODA_600-ALT_MODTAGER_BP").text = receiver_cpr
    session.findById("wnd[1]").sendVKey(0)

    _handle_word_window()

    letter_sent = False

    popup = session.findById("wnd[2]", False)
    if popup and popup.text == "Opret Forretningspartner":
        session.findById("wnd[2]/usr/btnBUTTON_1").press()

    popup = session.findById("wnd[2]", False)
    if popup and session.findById("wnd[2]/usr/txtMESSTXT1").text == "Der kan ikke sendes Digital Post til den valgte":
        # Dismiss popup and cancel
        session.findById("wnd[2]/tbar[0]/btn[0]").press()
        session.findById("wnd[1]/tbar[0]/btn[2]").press()
    else:
        # Send letter
        session.findById("wnd[1]/tbar[0]/btn[8]").press()
        letter_sent = True

    return letter_sent


def _set_clipboard(text: str) -> None:
    """Set text to the clipboard.

    Args:
        text: Text to set to clipboard.
    """
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(text)
    win32clipboard.CloseClipboard()


def _handle_word_window():
    # Save and close word file
    word = uiautomation.WindowControl(searchDepth=1, RegexName="Download.docm", ClassName="OpusApp")
    # Finding word sometimes fails. Try a few times
    for _ in range(5):
        try:
            word.Exists(maxSearchSeconds=20)
            break
        except COMError:
            pass
    else:
        raise RuntimeError("Word window not found.")

    word.SendKeys("{ctrl}w{ctrl}w", interval=0.5)
