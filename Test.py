import re  # Added to handle regex cleaning
from datetime import datetime

import requests
from bs4 import BeautifulSoup


def parse_table_one(table):
    """ Parses table with Financial Statement and Price Sensitive Information """
    table_data = {}
    rows = table.find_all('tr')
    for row in rows:
        th = row.find('th')
        td = row.find('td')
        if th and td:
            key = th.get_text(strip=True)
            value = td.get_text(strip=True)
            table_data[key] = value
    return table_data


def parse_dividend_table(table):
    """ Parses the dividend-related table and extracts key-value pairs """
    table_data = {}
    rows = table.find_all('tr')

    # Loop through the rows and extract <th> and <td> pairs
    for row in rows:
        th = row.find('th')
        td = row.find('td')

        if th and td:
            key = th.get_text(strip=True)
            value = td.get_text(strip=True)
            table_data[key] = value

    return table_data


def parse_table_two(table):
    table_data = {}
    rows = table.find_all('tr')

    # Loop through the rows and extract <th> and <td> pairs
    for row in rows:
        # Find the th and td tags, excluding rows that contain an inner table
        if not row.find('table'):  # Skip the rows that contain the inner table
            ths = row.find_all('th')
            tds = row.find_all('td')

            # If we have two <th> and two <td> (structured in pairs)
            if len(ths) == 2 and len(tds) == 2:
                key1 = ths[0].get_text(strip=True)
                value1 = tds[0].get_text(strip=True)
                key2 = ths[1].get_text(strip=True)
                value2 = tds[1].get_text(strip=True)

                # Add to the dictionary
                table_data[key1] = value1
                table_data[key2] = value2

    return table_data


def parse_table_three(table):
    """ Parses table with P/E Ratio for specific dates """
    table_data = {}
    rows = table.find_all('tr')

    # Get the header row
    header_row = rows[0]
    date_columns = [col.get_text(strip=True) for col in header_row.find_all('td')[1:]]

    # Loop through the data rows
    for row in rows[1:]:
        cols = row.find_all('td')
        key = cols[0].get_text(strip=True)  # Particulars
        data = [col.get_text(strip=True) for col in cols[1:]]
        table_data[key] = dict(zip(date_columns, data))

    return table_data


def parse_table_four(table):
    """ Parses table with Capital, Instrument Type, Market Lot, and Sector Information """
    table_data = {}
    rows = table.find_all('tr')

    # Loop through the rows and extract <th> and <td> pairs
    for row in rows:
        ths = row.find_all('th')
        tds = row.find_all('td')

        # If we have two <th> and two <td> (structured in pairs)
        if len(ths) == 2 and len(tds) == 2:
            key1 = ths[0].get_text(strip=True)
            value1 = tds[0].get_text(strip=True)
            key2 = ths[1].get_text(strip=True)
            value2 = tds[1].get_text(strip=True)

            # Add to the dictionary
            table_data[key1] = value1
            table_data[key2] = value2

    return table_data


def parse_date_string(date_string):
    """ Parses the date from strings like 'as on Jun 30, 2023' and formats it as '01/06/2023' """
    # Clean up the input string by removing unnecessary characters such as brackets and extra spaces
    date_string = re.sub(r'\(.*?\)', '', date_string)  # Remove text in parentheses (e.g., "(year ended)")
    date_string = date_string.replace('\r', '').replace('\n', '').replace(']', '').replace('[', '').strip()

    # Extract the part of the string that contains the date
    parts = date_string.split('as on')[-1].strip().split()

    # Convert the date to 'DD/MM/YYYY' format
    if len(parts) == 3:
        day = '01'  # Use '01' as the default day since it's not included in the string
        month_str = parts[0]  # e.g., 'Jun'
        year = parts[2]  # e.g., '2023'

        # Convert the month abbreviation to a number
        try:
            month = datetime.strptime(month_str, '%b').strftime('%m')
        except ValueError:
            return date_string  # Return the original string if the date parsing fails

        # Return the formatted date
        return f"{day}/{month}/{year}"

    return date_string  # If the format doesn't match, return the original string


def parse_shareholding_table(table):
    """ Parses the shareholding table and extracts data based on different months """
    table_data = {}
    rows = table.find_all('tr')

    # Loop through the rows and extract the relevant data
    for row in rows:
        tds = row.find_all('td')

        # Check if the row contains shareholding data (nested table)
        for td in tds:
            nested_table = td.find('table')
            if nested_table:
                date_key = tds[0].get_text(strip=True)  # Extract date information from the first td
                formatted_date = parse_date_string(date_key)  # Format the date as 'DD/MM/YYYY'
                shareholdings = {}

                # Now we process the inner nested table for shareholding data
                nested_rows = nested_table.find_all('tr')
                for nested_row in nested_rows:
                    cells = nested_row.find_all('td')
                    if len(cells) == 5:  # Ensure there are 5 columns for shareholding data
                        shareholdings['Sponsor/Director'] = cells[0].get_text(strip=True).replace('Sponsor/Director:',
                                                                                                  '').strip()
                        shareholdings['Govt'] = cells[1].get_text(strip=True).replace('Govt:', '').strip()
                        shareholdings['Institute'] = cells[2].get_text(strip=True).replace('Institute:', '').strip()
                        shareholdings['Foreign'] = cells[3].get_text(strip=True).replace('Foreign:', '').strip()
                        shareholdings['Public'] = cells[4].get_text(strip=True).replace('Public:', '').strip()

                # Store the shareholding data for this particular date
                table_data[formatted_date] = shareholdings

        # Handle non-nested rows (e.g., Listing Year, Market Category, Remarks)
        if len(tds) == 2 and not tds[1].find('table'):
            key = tds[0].get_text(strip=True)
            value = tds[1].get_text(strip=True)
            table_data[key] = value

    return table_data


def parse_eps_table_with_dates(table):
    """ Parses the EPS table and extracts EPS values along with their associated dates """
    table_data = {}
    rows = table.find_all('tr')

    headers = []
    current_section = None
    date_mapping = []

    # Loop through the rows
    for row in rows:
        # Check if it's a header row (e.g., Earnings Per Share (EPS))
        if 'Earnings Per Share (EPS)' in row.get_text():
            current_section = row.get_text(strip=True)
            table_data[current_section] = {}
            headers = []  # Reset headers for each section
            continue

        # Check if this is the row with quarter labels or the row with dates
        if 'Ending on' in row.get_text():
            date_mapping = [td.get_text(strip=True) for td in row.find_all('td')]
            continue

        if len(row.find_all('td')) > 5 and 'Particulars' not in row.get_text() and not date_mapping:
            headers = [td.get_text(strip=True) for td in row.find_all('td')]

        # Extract Basic/Diluted EPS and other details
        if 'Basic' in row.get_text() or 'Diluted' in row.get_text() or 'Market price per share' in row.get_text():
            cols = row.find_all('td')
            key = cols[0].get_text(strip=True)
            values = [col.get_text(strip=True) for col in cols[1:]]

            # Ensure that the length of values and headers/date_mapping are the same
            if len(values) == len(headers[1:]) == len(date_mapping[1:]):  # Skip the "Particulars" column
                table_data[current_section][key] = {
                    headers[i + 1]: {'value': values[i], 'date': date_mapping[i + 1]}  # +1 to skip "Particulars"
                    for i in range(len(values))
                }
            else:
                # Handle cases where lengths don't match
                print(f"Warning: Mismatched lengths in {key} row. Skipping this row.")
                continue

    return table_data


def parse_company_info_table(table):
    """ Parses the company info table and extracts key-value pairs """
    company_info = {}
    rows = table.find_all('tr')

    # Loop through the rows and extract relevant data
    for row in rows:
        tds = row.find_all('td')

        # If the row has 3 columns, extract key from the first column and value from the last column
        if len(tds) == 3:
            key = tds[1].get_text(strip=True)
            value = tds[2].get_text(strip=True)
            company_info[key] = value

        # If the row has 2 columns, it's typically for the short/long-term loans
        elif len(tds) == 2:
            key = tds[0].get_text(strip=True)
            value = tds[1].get_text(strip=True)
            company_info[key] = value

    return company_info


def parse_address_info_table(table):
    """ Parses the address and contact info table and extracts key-value pairs """
    contact_info = {}
    rows = table.find_all('tr')

    # Loop through the rows and extract relevant data
    for row in rows:
        tds = row.find_all('td')

        # Handle the row with three columns (e.g., Address, Factory)
        if len(tds) == 3:
            key = tds[1].get_text(strip=True)  # Extract the key (e.g., Head Office, Factory)
            value = tds[2].get_text(strip=True)  # Extract the value (e.g., the address)
            contact_info[key] = value

        # Handle rows with two columns and colspan attributes (e.g., Fax, E-mail)
        elif len(tds) == 2:
            key = tds[0].get_text(strip=True)  # Extract the key (e.g., Fax, Contact Phone)
            value = tds[1].get_text(strip=True)  # Extract the value
            contact_info[key] = value

    return contact_info


def extract_basic_eps(table):
    """ Extracts Basic EPS values for each quarter """
    eps_data = {}
    rows = table.find_all('tr')

    # Track whether we are in the right section (Basic EPS)
    in_eps_section = False

    # Loop through the rows and extract relevant data
    for row in rows:
        tds = row.find_all('td')
        if len(tds) == 7:
            # Look for the section labeled "Earnings Per Share (EPS)" or "Basic"
            if "Earnings Per Share (EPS)" in tds[0].get_text():
                in_eps_section = True
            elif "Basic" in tds[0].get_text() and in_eps_section:
                # Extract the Basic EPS values for the quarters
                eps_data['Q1'] = tds[1].get_text(strip=True)
                eps_data['Q2'] = tds[2].get_text(strip=True)
                eps_data['Half Yearly'] = tds[3].get_text(strip=True)
                eps_data['Q3'] = tds[4].get_text(strip=True)
                eps_data['9 Months'] = tds[5].get_text(strip=True)
                eps_data['Annual'] = tds[6].get_text(strip=True)
                break  # We've extracted the data, so we can stop here

    return eps_data


if __name__ == '__main__':
    # URL of the page you want to scrape
    url = 'https://dsebd.org/displayCompany.php?name=RENATA'

    # Send a GET request to the website
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Dictionary to hold the parsed key-value data
        all_tables_data = []

        # Find all tables with the class "table table-bordered background-white"
        company_tables = soup.find_all('table', class_='table table-bordered background-white')

        # Loop through each table
        for idx, table in enumerate(company_tables):
            # print(table)
            # print("Index" + str(idx))
            # Logic to handle different table structures
            if idx == 0:
                print(f"\nTable {idx + 1} (Financial Statement and Price Sensitive Information):")
                table_data = parse_table_one(table)
                print(table_data)
            elif idx == 1:
                print(f"\nTable {idx + 1} (Basic Information):")
                table_data = parse_table_two(table)
                print(table_data)
            elif idx == 2:
                print(f"\nTable {idx + 1} (Dividend Information):")
                table_data = parse_dividend_table(table)
                print(table_data)
            # elif idx == 3:
            #     print(f"\nTable {idx + 1} (Interim Financial Performance):")
            #     table_data = parse_eps_table_with_dates(table)
            #     print(table_data)
            elif idx == 3:
                print(f"\nTable {idx + 1} (Interim Financial Performance:")
                table_data = extract_basic_eps(table)
                print(table_data)
            elif idx == 9:
                print(f"\nTable {idx + 1} (Share Holding Information):")
                table_data = parse_shareholding_table(table)
                print(table_data)
            elif idx == 10:
                print(f"\nTable {idx + 1} (Corporate Performance at a glance):")
                table_data = parse_company_info_table(table)
                print(table_data)
            elif idx == 11:
                print(f"\nTable {idx + 1} (Address of the Company):")
                table_data = parse_address_info_table(table)
                print(table_data)
            else:
                print("nothing")

            # Append this table's data to the list of all tables' data
            all_tables_data.append(table_data)

    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")
