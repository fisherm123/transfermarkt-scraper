from tfmkt.spiders.common import BaseSpider
from scrapy.shell import Response
from scrapy.shell import inspect_response # required for debugging
from urllib.parse import unquote, urlparse
import re
import json

class PlayersSpider(BaseSpider):
  name = 'players'

  def parse(self, response, parent):
      """Parse clubs's page to collect all player's urls.

        @url https://www.transfermarkt.co.uk/sc-braga/startseite/verein/1075/saison_id/2019
        @returns requests 37 37
        @cb_kwargs {"parent": "dummy"}
      """

      # uncommenting the two lines below will open a scrapy shell with the context of this request
      # when you run the crawler. this is useful for developing new extractors

      # inspect_response(response, self)
      # exit(1)

      players_table = response.xpath("//div[@class='responsive-table']")
      assert len(players_table) == 1

      players_table = players_table[0]

      player_hrefs = players_table.xpath('//table[@class="inline-table"]//td[@class="hauptlink"]/a/@href').getall()

      for href in player_hrefs:
          
        cb_kwargs = {
          'base' : {
            'type': 'player',
            'href': href,
          }
        }

        yield response.follow(href, self.parse_details, cb_kwargs=cb_kwargs)

  def parse_details(self, response, base):
    """Extract player details from the main page.
    It currently only parses the PLAYER DATA section.

      @url https://www.transfermarkt.co.uk/steven-berghuis/profil/spieler/129554
      @returns items 1 1
      @cb_kwargs {"base": {"href": "some_href/code", "type": "player", "parent": {}}}
      @scrapes href type parent name last_name number
    """

    # uncommenting the two lines below will open a scrapy shell with the context of this request
    # when you run the crawler. this is useful for developing new extractors

    # inspect_response(response, self)
    # exit(1)

    # parse 'PLAYER DATA' section

    attributes = {}

    name_element = response.xpath("//h1[@class='data-header__headline-wrapper']")
    attributes["name"] = self.safe_strip("".join(name_element.xpath("text()").getall()).strip())
    attributes["last_name"] = self.safe_strip(name_element.xpath("strong/text()").get())
    attributes["number"] = self.safe_strip(name_element.xpath("span/text()").get())

    attributes['date_of_birth'] = response.xpath("//span[text()='Date of birth:']/following::span[1]//text()").get()
    attributes['place_of_birth'] = {
      'country': response.xpath("//span[text()='Place of birth:']/following::span[1]/span/img/@title").get(),
      'city': response.xpath("//span[text()='Place of birth:']/following::span[1]/span/text()").get()
    }
    attributes['age'] = response.xpath("//span[text()='Age:']/following::span[1]/text()").get()
    attributes['height'] = response.xpath("//span[text()='Height:']/following::span[1]/text()").get()
    attributes['citizenship'] = response.xpath("//span[text()='Citizenship:']/following::span[1]/img/@title").get()
    attributes['position'] = self.safe_strip(response.xpath("//span[text()='Position:']/following::span[1]/text()").get())

    attributes['image_url'] = response.xpath("//img[@class='data-header__profile-image']/@src").get()
    attributes['current_club'] = {
      'href': response.xpath("//span[contains(text(),'Current club:')]/following::span[1]/a/@href").get()
    }

    attributes['national_team'] = response.xpath("//li[contains(text(), 'Current international:')]/span/a/text()").get()
    attributes['foot'] = response.xpath("//span[text()='Foot:']/following::span[1]/text()").get()
  

    attributes['current_market_value_start'] = self.safe_strip(response.xpath("//a[@class='data-header__market-value-wrapper']/text()").get())
    attributes['current_market_value_end'] = self.safe_strip(response.xpath("//a[@class='data-header__market-value-wrapper']/span[2]/text()").get())

    attributes['code'] = unquote(urlparse(base["href"]).path.split("/")[1])

    yield {
      **base,
      **attributes
    }

  def parse_market_history(self, response: Response):
    """
    Parse player's market history from the graph
    """
    pattern = re.compile('\'data\'\:.*\}\}]')

    try:
      parsed_script = json.loads(
        '{' + response.xpath("//script[contains(., 'series')]/text()").re(pattern)[0].replace("\'", "\"").encode().decode('unicode_escape') + '}'
      )
      return parsed_script["data"]
    except Exception as err:
      self.logger.warning("Failed to scrape market value history from %s", response.url)
      return None
