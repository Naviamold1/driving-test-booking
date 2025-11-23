import requests
import typing as t
import logging
from discord_webhook import DiscordWebhook, DiscordEmbed
from datetime import datetime

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


Locations = t.Literal[
    "Kutaisi",
    "Batumi",
    "Telavi",
    "Akhaltsikhe",
    "Zugdidi",
    "Gori",
    "Poti",
    "Ozurgeti",
    "Sachkhere",
    "Rustavi",
]


class License:
    def __init__(self, center: Locations) -> None:
        self.center: Locations = center
        self.dates: list[t.Never] | list[LocationInfo] = []  # pyright: ignore[reportRedeclaration]
    
    def get_data(self):
        url = "https://api-my.sa.gov.ge/api/v1/DrivingLicensePracticalExams2/DrivingLicenseExamsDates2"
        time_url = "https://api-my.sa.gov.ge/api/v1/DrivingLicensePracticalExams2/DrivingLicenseExamsDateFrames2"

        obj: dict[str, int] = {
            "Kutaisi": 2,
            "Batumi": 3,
            "Telavi": 4,
            "Akhaltsikhe": 5,
            "Zugdidi": 6,
            "Gori": 7,
            "Poti": 8,
            "Ozurgeti": 9,
            "Sachkhere": 10,
            "Rustavi": 15,
        }

        querystring = {"CategoryCode": "4", "CenterId": obj[self.center]}

        headers = {"accept": "application/json, text/plain, */*", "accept-language": "ka"}

        response = requests.get(url, headers=headers, params=querystring)
        self.dates: list[t.Never] | list[LocationInfo] = response.json()
        if self.dates == []:
            return self

        for date in self.dates:
            querystring["ExamDate"] = datetime.strptime(
                date["bookingDate"], "%d-%m-%Y"
            ).strftime("%Y-%m-%d")
            print(querystring)
            time_res: list[dict[str, str]] = requests.get(  # pyright: ignore[reportAny]
                time_url, headers=headers, params=querystring
            ).json()
            date["examTimes"] = [i["timeFrameName"] for i in time_res]
        logger.info(self.dates)

        return self
    
    def send_webhook(self) -> None:
        if self.dates == []:
            return

        webhook = DiscordWebhook(
            url="https://discord.com/api/webhooks/1441399079681916970/E7zyE4pgDaaF3Y8F0BTdvhH7GuQL83t2Lkg8GpLDst79-lvKmwCDzP5c3I2oZw0oHedd"
        )
        embed = DiscordEmbed(
            title="New Driving Test Dates Available!",
            description="The following dates are now open for booking:",
            color=0x00FF00,
        )
        embed.set_url("https://my.sa.gov.ge/drivinglicenses/practicalexam")
        for date in self.dates:
            embed.add_embed_field(
                name=f"{self.center} — {date['bookingDate']}",
                value=str(date["examTimes"])
                .removeprefix("[")
                .removesuffix("]")
                .replace("'", ""),
                inline=False,
            )
        embed.set_timestamp()
        webhook.add_embed(embed)
        response = webhook.execute()
        if response.status_code == 200:
            logger.info("Webhook sent successfully.")
        else:
            logger.error(f"Failed to send webhook. Status code: {response.status_code}")



def main() -> None:
    License("Rustavi").get_data().send_webhook()
    License("Gori").get_data().send_webhook()

if __name__ == "__main__":
    main()
