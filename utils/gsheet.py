import time
import gspread
from gspread import exceptions


class GSheet:

    def __init__(self):
        self.gc = gspread.service_account(filename="./deerhacks-bot-f52cc30d39c9.json")
        self.sh = self.gc.open("QR Code System (DeerHacks)")

    def retrieve_tokens(self):
        tokens = []
        wks = self.sh.worksheet("[IMPORT] Participant Data")

        # Get the data from columns A for each row
        max_retries = 5
        retries = 0

        while retries < max_retries:

            try:
                tokens = list(map(lambda i: f"https://chart.googleapis.com/chart?chs=150x150&cht=qr&chl={i[0]}", wks.get('A2:A')))

            except exceptions.APIError as e:
                print(f"Possibly Rate limited? {e} Waiting 100 seconds...")
                time.sleep(100)
                retries += 1

            else:
                break

        if len(tokens) == 0:
            print("Failed to get tokens after multiple tries")
            return

        return tokens

    def inperson_sheet(self):

        attendees = []
        temp = []

        wks = self.sh.worksheet("OPEN WHEN SCANNING")

        # Get the data from columns A for each row
        max_retries = 5
        retries = 0

        while retries < max_retries:

            try:
                temp = wks.get('G2:G')

            except exceptions.APIError as e:
                print(f"Possibly Rate limited? {e} Waiting 100 seconds...")
                time.sleep(100)
                retries += 1

            else:
                break

        if len(temp) == 0:
            print("Failed to get attendees.")
            return []

        for i in temp:
            if i:
                attendees.append(i[0])

        return attendees



    def registration_sheet(self):

        participants = {}
        wks = self.sh.worksheet("[IMPORT] Participant Data")

        # Get the data from columns D and F for each row
        max_retries = 5
        retries = 0

        column_d_data = []
        column_f_data = []

        while retries < max_retries:

            try:
                column_d_data = wks.get('D2:D')
                column_f_data = wks.get('F2:F')

            except exceptions.APIError as e:
                print(f"Possibly Rate limited? {e} Waiting 100 seconds...")
                time.sleep(100)
                retries += 1

            else:
                break

        if len(column_d_data) == 0 and len(column_f_data) == 0:
            print("Failed to get data after multiple retries")
            return {}

        while len(column_d_data) < len(column_f_data):
            column_d_data.append([])

        while len(column_d_data) > len(column_f_data):
            column_f_data.append([])

        for p, k in zip(column_d_data, column_f_data):

            email = p[0] if len(p) > 0 else ""
            username = k[0] if len(k) > 0 else ""

            if username:
                participants[username] = email

        return participants


if __name__ == '__main__':
    x = GSheet()
    print(x.inperson_sheet())