import enum
import logging
import os
import typing as t
from datetime import datetime
from json import JSONDecodeError

import requests
from discord_webhook import DiscordEmbed, DiscordWebhook
from dotenv import load_dotenv
from requests.sessions import Session

load_dotenv()  # pyright: ignore[reportUnusedCallResult]

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(name)-12s %(levelname)-8s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class LocationInfo(t.TypedDict):
    bookingDate: str
    bookingDateStatus: int
    examTimes: list[str]


class Locations(enum.IntEnum):
    KUTAISI = 2
    BATUMI = 3
    TELAVI = 4
    AKHALTSIKHE = 5
    ZUGDIDI = 6
    GORI = 7
    POTI = 8
    OZURGETI = 9
    SACHKHERE = 10
    RUSTAVI = 15


class License:
    def __init__(self, center: Locations) -> None:
        self.center: Locations = center

        self.dates: list[t.Never] | list[LocationInfo] = []  # pyright: ignore[reportRedeclaration]

        # Requests Session Config
        self.session: Session = requests.Session()
        self.session.headers.update(
            {
                "accept": "application/json, text/plain, */*",
                "accept-language": "ka",
                "user-agent": "Mozilla/5.0 (Compatible; LicenseMonitor/1.0)",
            }
        )

    def get_data(self):
        """
        Gets data from  self.center

        :params None
        :returns Self
        """

        DATES_URL = "https://api-bookings.sa.gov.ge/api/v1/DrivingLicensePracticalExams2/DrivingLicenseExamsDates2"
        TIMES_URL = "https://api-bookings.sa.gov.ge/api/v1/DrivingLicensePracticalExams2/DrivingLicenseExamsDateFrames2"

        querystring = {"CategoryCode": "4", "CenterId": self.center}

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "ka",
        }

        response = self.session.get(DATES_URL, headers=headers, params=querystring)
        try:
            self.dates: list[t.Never] | list[LocationInfo] = response.json()
            if self.dates == []:
                logger.info(f"No available dates in {self.center.name}")
                return self

            for date in self.dates:
                querystring["ExamDate"] = datetime.strptime(
                    date["bookingDate"], "%d-%m-%Y"
                ).strftime("%Y-%m-%d")
                time_res: list[dict[str, str]] = self.session.get(  # pyright: ignore[reportAny]
                    TIMES_URL, headers=headers, params=querystring
                ).json()
                date["examTimes"] = [i["timeFrameName"] for i in time_res]
            logger.info(self.dates)
        except JSONDecodeError:
            logger.error(f"API returned unkown response: `{response.text}`")
        return self

    def send_webhook(self) -> None:
        """
        Sends discord webhook via provided discord webhook url
        """

        if self.dates == []:
            return

        DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
        if DISCORD_WEBHOOK_URL is None:
            raise ValueError(".env file doesn't contains DISCORD_WEBHOOK_URL")

        webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
        embed = DiscordEmbed(
            title=f"🚗 New Driving Test Dates Available in {self.center.name}!",
            description=f"The following **{len(self.dates)}** dates are now open for booking in **{self.center.name.capitalize()}**:",
            color=0x00FF00,  # Green
        )
        embed.set_url("https://my.sa.gov.ge/drivinglicenses/practicalexam")
        for date in self.dates[:25]:
            embed.add_embed_field(
                name=f"{self.center.name.capitalize()} — {date['bookingDate']}",
                value=str(date["examTimes"])
                .removeprefix("[")
                .removesuffix("]")
                .replace("'", ""),
                inline=False,
            )
        embed.set_footer(f"Checked {self.center.name.capitalize()}")  # pyright: ignore[reportUnknownMemberType]
        embed.set_timestamp()
        webhook.add_embed(embed)
        response = webhook.execute()
        if response.status_code == 200:
            logger.info("Webhook sent successfully.")
        else:
            logger.error(f"Failed to send webhook. Status code: {response.status_code}")


def main() -> None:
    License(Locations.RUSTAVI).get_data().send_webhook()
    License(Locations.GORI).get_data().send_webhook()


if __name__ == "__main__":
    main()
