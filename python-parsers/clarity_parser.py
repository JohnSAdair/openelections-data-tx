import clarify
import requests
import zipfile
import csv
import os
import logging
from collections import defaultdict

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO, BytesIO

def statewide_results(url):
    j = clarify.Jurisdiction(url=url, level="state")
    r = requests.get("http://results.enr.clarityelections.com/WV/74487/207685/reports/detailxml.zip", stream=True)
    z = zipfile.ZipFile(BytesIO(r.content))
    z.extractall()
    p = clarify.Parser()
    p.parse("detail.xml")
    results = []
    for result in p.results:
        candidate = result.choice.text
        office, district = parse_office(result.contest.text)
        party = parse_party(result.contest.text)
        if '(' in candidate and party is None:
            if '(I)' in candidate:
                if '(I)(I)' in candidate:
                    candidate = candidate.split('(I)')[0]
                    party = 'I'
                else:
                    candidate, party = candidate.split('(I)')
                candidate = candidate.strip() + ' (I)'
            else:
                print(candidate)
                candidate, party = candidate.split('(', 1)
                candidate = candidate.strip()
            party = party.replace(')','').strip()
        if result.jurisdiction:
            county = result.jurisdiction.name
        else:
            county = None
        r = [x for x in results if x['county'] == county and x['office'] == office and x['district'] == district and x['party'] == party and x['candidate'] == candidate]
        if r:
             r[0][result.vote_type] = result.votes
        else:
            results.append({ 'county': county, 'office': office, 'district': district, 'party': party, 'candidate': candidate, result.vote_type: result.votes})

    with open("20180508__wv__general.csv", "wt") as csvfile:
        w = csv.writer(csvfile)
        w.writerow(['county', 'office', 'district', 'party', 'candidate', 'votes'])
        for row in results:
            total_votes = row['Election Day']# + row['Absentee by Mail'] + row['Advance in Person'] + row['Provisional']
            w.writerow([row['county'], row['office'], row['district'], row['party'], row['candidate'], total_votes])

def download_county_files(url, filename):
    no_xml = []
    j = clarify.Jurisdiction(url=url, level="state")
    subs = j.get_subjurisdictions()
    for sub in subs:
        try:
            r = requests.get(sub.report_url('xml'), stream=True)
            z = zipfile.ZipFile(BytesIO(r.content))
            z.extractall()
            precinct_results(sub.name.replace(' ','_').lower(),filename)
        except:
            no_xml.append(sub.name)

    print(no_xml)

def add_voter_turnout_rows(results, parser, county_name):
    """
    Add Registered Voters and Ballots Cast as separate office rows.
    
    Args:
        results (defaultdict): Existing results dictionary
        parser: Clarify parser object with parsed data
        county_name (str): County name
    """
    import xml.etree.ElementTree as ET
    
    # Calculate ballots cast by precinct and vote method
    import clarify
import requests
import zipfile
import csv
import os
import logging
from collections import defaultdict

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO, BytesIO

def statewide_results(url):
    j = clarify.Jurisdiction(url=url, level="state")
    r = requests.get("http://results.enr.clarityelections.com/WV/74487/207685/reports/detailxml.zip", stream=True)
    z = zipfile.ZipFile(BytesIO(r.content))
    z.extractall()
    p = clarify.Parser()
    p.parse("detail.xml")
    results = []
    for result in p.results:
        candidate = result.choice.text
        office, district = parse_office(result.contest.text)
        party = parse_party(result.contest.text)
        if '(' in candidate and party is None:
            if '(I)' in candidate:
                if '(I)(I)' in candidate:
                    candidate = candidate.split('(I)')[0]
                    party = 'I'
                else:
                    candidate, party = candidate.split('(I)')
                candidate = candidate.strip() + ' (I)'
            else:
                print(candidate)
                candidate, party = candidate.split('(', 1)
                candidate = candidate.strip()
            party = party.replace(')','').strip()
        if result.jurisdiction:
            county = result.jurisdiction.name
        else:
            county = None
        r = [x for x in results if x['county'] == county and x['office'] == office and x['district'] == district and x['party'] == party and x['candidate'] == candidate]
        if r:
             r[0][result.vote_type] = result.votes
        else:
            results.append({ 'county': county, 'office': office, 'district': district, 'party': party, 'candidate': candidate, result.vote_type: result.votes})

    with open("20180508__wv__general.csv", "wt") as csvfile:
        w = csv.writer(csvfile)
        w.writerow(['county', 'office', 'district', 'party', 'candidate', 'votes'])
        for row in results:
            total_votes = row['Election Day']# + row['Absentee by Mail'] + row['Advance in Person'] + row['Provisional']
            w.writerow([row['county'], row['office'], row['district'], row['party'], row['candidate'], total_votes])

def download_county_files(url, filename):
    no_xml = []
    j = clarify.Jurisdiction(url=url, level="state")
    subs = j.get_subjurisdictions()
    for sub in subs:
        try:
            r = requests.get(sub.report_url('xml'), stream=True)
            z = zipfile.ZipFile(BytesIO(r.content))
            z.extractall()
            precinct_results(sub.name.replace(' ','_').lower(),filename)
        except:
            no_xml.append(sub.name)

    print(no_xml)

def add_voter_turnout_rows(results, parser, county_name):
    """
    Add Registered Voters and Ballots Cast as separate office rows.
    
    Args:
        results (defaultdict): Existing results dictionary
        parser: Clarify parser object with parsed data
        county_name (str): County name
    """
    import xml.etree.ElementTree as ET
    
    # Try to read the XML file directly to get voter turnout data
    try:
        tree = ET.parse("detail.xml")
        root = tree.getroot()
        
        # Look for VoterTurnout element
        voter_turnout_elem = root.find('.//VoterTurnout')
        if voter_turnout_elem is not None:
            # First, add Registered Voters from precinct attributes
            precincts = voter_turnout_elem.findall('.//Precinct')
            for precinct in precincts:
                precinct_name = precinct.get('name')
                if precinct_name:
                    total_voters = precinct.get('totalVoters', '0')
                    ballots_cast = precinct.get('ballotsCast', '0')
                    
                    # Add Registered Voters row
                    if total_voters and total_voters != '0':
                        reg_key = (county_name, precinct_name, 'Registered Voters', None, None, None)
                        # For Registered Voters, only populate the votes column (no vote type breakdown)
                        results[reg_key]['votes_only'] = int(total_voters)
                    
                    # Add basic Ballots Cast row with total in a vote type column
                    if ballots_cast and ballots_cast != '0':
                        ballots_key = (county_name, precinct_name, 'Ballots Cast', None, None, None)
                        # Don't add to 'Total' column - let it be calculated from vote_data
                        results[ballots_key]['ballotsCast'] = int(ballots_cast)
            
            # Now check if there are VoteType breakdowns in the VoterTurnout section
            vote_types = voter_turnout_elem.findall('.//VoteType')
            if vote_types:
                # VoteType breakdowns exist - use them for Ballots Cast
                for vote_type in vote_types:
                    vote_type_name = vote_type.get('name')
                    if vote_type_name and vote_type_name != 'regVotersCounty':
                        # Find precincts within this vote type
                        precincts = vote_type.findall('.//Precinct')
                        for precinct in precincts:
                            precinct_name = precinct.get('name')
                            votes = precinct.get('votes', '0')
                            if precinct_name and votes and votes != '0':
                                ballots_key = (county_name, precinct_name, 'Ballots Cast', None, None, None)
                                results[ballots_key][vote_type_name] = int(votes)
            else:
                # No VoteType breakdowns - Ballots Cast will just have the total votes value
                print("No VoteType breakdowns found in VoterTurnout - using total ballots cast only")
        else:
            print("VoterTurnout element not found in XML")
            
    except Exception as e:
        print(f"Error reading voter turnout data: {e}")
        # Try alternative method using regVotersCounty from parser results
        reg_voters_data = {}
        for result in parser.results:
            if result.vote_type == 'regVotersCounty' and result.jurisdiction:
                precinct_name = result.jurisdiction.name
                if precinct_name and result.votes:
                    if precinct_name not in reg_voters_data:
                        reg_voters_data[precinct_name] = 0
                    reg_voters_data[precinct_name] += result.votes
        
        # Add registered voter rows from regVotersCounty data
        for precinct, reg_voters in reg_voters_data.items():
            if reg_voters > 0:
                reg_key = (county_name, precinct, 'Registered Voters', None, None, None)
                results[reg_key]['votes_only'] = reg_voters

def precinct_results(county_name, filename):
    """
    Parse precinct-level election results from detail.xml and output to CSV.
    
    Args:
        county_name (str): Name of the county
        filename (str): Base filename for output CSV
    """
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    f = filename + '__' + county_name + '__precinct.csv'
    
    # Check if detail.xml exists
    if not os.path.exists("detail.xml"):
        logger.error("detail.xml not found")
        return False
    
    try:
        p = clarify.Parser()
        p.parse("detail.xml")
    except Exception as e:
        logger.error(f"Failed to parse detail.xml: {e}")
        return False
    
    # Use defaultdict to simplify result aggregation
    results = defaultdict(lambda: defaultdict(int))
    vote_types = set()
    
    # Filter out unwanted vote types upfront (keep regVotersCounty now)
    excluded_vote_types = {'Number of Precincts', 'Overvotes', 'Undervotes'}
    
    for result in p.results:
        # Skip excluded vote types
        if result.vote_type in excluded_vote_types:
            continue
            
        # Skip results without choices (these are typically summary rows)
        if result.choice is None:
            continue
            
        vote_types.add(result.vote_type)
        
        # Extract candidate information
        candidate = result.choice.text.strip() if result.choice.text else ""
        if not candidate:
            continue
            
        # Parse office and district
        office, district = parse_office(result.contest.text)
        
        # Get party information
        party = result.choice.party if hasattr(result.choice, 'party') else None
        
        # Handle party parsing from candidate name if not available
        if '(' in candidate and party is None:
            candidate, party = parse_candidate_party(candidate)
        
        # Clean up candidate name - remove party prefixes
        candidate = clean_candidate_name(candidate)
        
        # Get geographic information
        county = p.region if hasattr(p, 'region') else county_name
        precinct = result.jurisdiction.name if result.jurisdiction else None
        
        # Skip results without precinct information
        if precinct is None:
            continue
        
        # Create unique key for this candidate/race combination
        key = (county, precinct, office, district, party, candidate)
        
        # Aggregate votes by vote type
        results[key][result.vote_type] = result.votes
    
    # Add voter turnout data as separate office rows
    add_voter_turnout_rows(results, p, county_name)
    
    # Convert to list format for CSV output
    output_rows = []
    for key, vote_data in results.items():
        county, precinct, office, district, party, candidate = key
        
        # Handle special party cases
        if 'Republican' in office:
            party = 'REP'
        elif 'Democrat' in office:
            party = 'DEM'
        
        # Calculate total votes
        if office == 'Registered Voters':
            # For Registered Voters, use the special votes_only value
            vote_total = vote_data.get('votes_only', 0)
        else:
            # For all other offices, sum all vote types
            vote_total = sum(v for k, v in vote_data.items() if k != 'votes_only')
        
        # Create row data
        row_data = {
            'county': county,
            'precinct': precinct,
            'office': office,
            'district': district,
            'party': party,
            'candidate': candidate,
            'votes': vote_total
        }
        
        # Add individual vote type columns
        for vt in vote_types:
            if vt != 'votes_only':  # Skip the special votes_only marker
                if office == 'Registered Voters':
                    # For Registered Voters, all vote method columns should be None (empty)
                    row_data[vt.replace(' ', '_').lower()] = ''
                else:
                    row_data[vt.replace(' ', '_').lower()] = vote_data.get(vt, 0)
        
        output_rows.append(row_data)
    
    # Sort results for consistent output
    output_rows.sort(key=lambda x: (x['office'], x['district'] or '', x['candidate']))
    
    # Write to CSV
    try:
        with open(f, "w", newline='', encoding='utf-8') as csvfile:
            if not output_rows:
                logger.warning("No results to write")
                return False
                
            # Prepare headers
            base_headers = ['county', 'precinct', 'office', 'district', 'party', 'candidate', 'votes']
            vote_type_headers = sorted([vt.replace(' ', '_').lower() for vt in vote_types])
            headers = base_headers + vote_type_headers
            
            w = csv.DictWriter(csvfile, fieldnames=headers)
            w.writeheader()
            
            for row in output_rows:
                # Ensure all fields are present
                output_row = {header: row.get(header, '') for header in headers}
                w.writerow(output_row)
                
        logger.info(f"Successfully wrote {len(output_rows)} rows to {f}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to write CSV file: {e}")
        return False


def clean_candidate_name(candidate_text):
    """
    Remove party prefixes from candidate names.
    
    Args:
        candidate_text (str): Candidate name that may have party prefix
        
    Returns:
        str: Clean candidate name without party prefix
    """
    if not candidate_text:
        return candidate_text
    
    candidate = candidate_text.strip()
    
    # Common party prefixes to remove
    party_prefixes = ['REP ', 'DEM ', 'LIB ', 'GRN ', 'IND ']
    
    for prefix in party_prefixes:
        if candidate.startswith(prefix):
            candidate = candidate[len(prefix):].strip()
            break
    
    return candidate


def parse_candidate_party(candidate_text):
    """
    Parse candidate name and party from combined text.
    
    Args:
        candidate_text (str): Combined candidate and party text
        
    Returns:
        tuple: (candidate_name, party)
    """
    candidate = candidate_text.strip()
    party = None
    
    if '(' in candidate:
        if '(I)' in candidate:
            if '(I)(I)' in candidate:
                # Handle double independent notation
                candidate = candidate.split('(I)')[0].strip()
                party = 'I'
            else:
                # Handle single independent notation
                parts = candidate.split('(I)')
                candidate = parts[0].strip()
                if len(parts) > 1 and parts[1].strip():
                    # Keep the (I) in the name if there's more text after it
                    candidate += ' (I)'
                party = 'I'
        else:
            # Handle other party notations
            try:
                candidate, party_part = candidate.split('(', 1)
                candidate = candidate.strip()
                party = party_part.replace(')', '').strip()
            except ValueError:
                # If split fails, keep original candidate
                pass
    
    return candidate, party


def parse_office(office_text):
    """
    Improved office and district parsing with standardized office names.
    
    Args:
        office_text (str): Office text to parse
        
    Returns:
        tuple: (office, district)
    """
    if not office_text:
        return "", None
    
    office_text = office_text.strip()
    
    # Handle different office text formats
    if ' - ' in office_text:
        office = office_text.split(' - ')[0].strip()
    elif ',' in office_text:
        office = office_text.split(',')[0].strip() 
    else:
        office = office_text
    
    # Extract district information
    district = None
    
    if ', District' in office_text:
        district_part = office_text.split(', District')[1]
        if ' - ' in district_part:
            district = district_part.split(' - ')[0].strip()
        else:
            district = district_part.strip()
    elif ', Dist' in office_text:
        district_part = office_text.split(', Dist')[1]
        if ' - ' in district_part:
            district = district_part.split(' - ')[0].strip()
        else:
            district = district_part.strip()
    elif 'Precinct' in office_text:
        # Handle precinct-level offices
        if 'Precinct' in office_text:
            precinct_part = office_text.split('Precinct')[1]
            district = precinct_part.strip()
    elif ', Pl ' in office_text:
        # Handle "Place" designations  
        place_part = office_text.split(', Pl ')[1]
        if ' - ' in place_part:
            district = place_part.split(' - ')[0].strip()
        else:
            district = place_part.strip()
    
    # Standardize office names
    if 'President/Vice President' in office:
        office = 'President'
    elif 'United States Senator' in office or 'US Senator' in office or "U. S. Senator" in office:
        office = 'U.S. Senate'
        district = None
    elif 'US Representative' in office or 'U.S. Representative' in office or "United States Representative" in office:
        office = 'U.S. House'
    
    return office, district


def parse_party(office_text):
    """
    Parse party information from office text.
    
    Args:
        office_text (str): Office text to parse
        
    Returns:
        str: Party abbreviation or None
    """
    if '- REP' in office_text:
        party = 'REP'
    elif '- DEM' in office_text:
        party = 'DEM'
    else:
        party = None
    return party