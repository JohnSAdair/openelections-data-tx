#!/usr/bin/env python3
"""
Complete PDF Election Data Extractor using pdfplumber
"""

import sys
import csv
import re
from typing import List, Dict

try:
    import pdfplumber
except ImportError:
    print("Please install pdfplumber: pip install pdfplumber")
    sys.exit(1)

def extract_text_with_layout(pdf_path: str) -> str:
    """Extract text from PDF preserving layout using pdfplumber."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def normalize_office_name(office: str) -> str:
    """Normalize office names according to specifications."""
    office = office.strip()
    
    if "President and Vice President" in office or "President and Vice-President" in office:
        return "President"
    elif "President/Vice President" in office:
        return "President"
    elif "President/Vice-President" in office:
        return "President"
    elif "United States Senator" in office:
        return "U.S. Senate"
    elif "U.S. Senator" in office:
        return "U.S. Senate"
    elif "United States Representative" in office:
        return "U.S. House"
    elif "U.S. Representative" in office:
        return "U.S. House"
    elif "State Senator" in office:
        return "State Senate"
    elif "State Representative" in office and "Unexpired Term" not in office:
        return "State Representative"
    elif "Chief Justice, 13th Court of Appeals" in office:
        return "Chief Justice, 13th Court of Appeals District"
    elif "Chief Justice, 10th Court of Appeals" in office:
        return "Chief Justice, 10th Court of Appeals District"
    elif "Chief Justice, 11th Court of Appeals District" in office:
        return "Chief Justice, 11th Court of Appeals District"
    
    return office

def parse_election_data(text: str, county: str) -> List[Dict]:
    """Parse election data from PDF text with preserved layout."""
    data = []
    lines = text.split('\n')
    
    current_precinct = None
    current_office = None
    district = ""
    precinct_added = set()
    
    office_patterns = [
        r'President and Vice President',
        r'President and Vice-President',
        r'President/Vice President',
        r'President/Vice-President',
        r'United States Senator',
        r'U.S. Senator',
        r'United States Representative[^\n]*',
        r'U.S. Representative[^\n]*',
        r'Railroad Commissioner',
        r'Justice[^\n]*',
        r'Judge[^\n]*',
        r'Member[^\n]*',
        r'State Representative[^\n]*',
        r'Chief Justice, 13th Court of Appeals District',
        r'Chief Justice, 10th Court of Appeals District',
        r'Chief Justice, 11th Court of Appeals District',
        r'District Judge[^\n]*',
        r'District Attorney[^\n]*',
        r'County [^\n]*',
        r'Sheriff',
        r'District Clerk',
        r'Presiding Judge[^\n]*',
        r'PROPOSITION [A-Z]',
        r'County Attorney',
        r'County Clerk',
        r'County Tax Assessor-Collector',
        r'County Constable',
        r'Constable',
        r'HEADWATER GROUNDWATER CONSERVATION DISTRICT',
    ]
    
    for i, line in enumerate(lines):
        try:
            line = line.strip()
            if not line:
                continue
            
            # Check for precinct info - handle numbers with commas
            precinct_match = re.search(r'^(\d+?(?:\s*-\s*[\w\s]+)?)\s+([\d,]+)\s+of\s+([\d,]+)\s+registered\s+voters', line)
            if precinct_match:
                raw_precinct = precinct_match.group(1).strip()
                current_precinct = raw_precinct #re.sub(r'\s*-\s*\w+$', '', raw_precinct)
                ballots_cast = int(precinct_match.group(2).replace(',', ''))
                registered_voters = int(precinct_match.group(3).replace(',', ''))
                
#                print(f"Processing precinct line: {line}")
#                print(f"Raw precinct: '{raw_precinct}', Clean precinct: '{current_precinct}'")
                
                if current_precinct not in precinct_added:
                    # Add registered voters
                    data.append({
                        'county': county,
                        'precinct': current_precinct,
                        'office': 'Registered Voters',
                        'district': '',
                        'party': '',
                        'candidate': '',
                        'votes': registered_voters,
                        'absentee': '',
                        'early_voting': '',
                        'election_day': ''
                    })
                    
                    # Add ballots cast
                    data.append({
                        'county': county,
                        'precinct': current_precinct,
                        'office': 'Ballots Cast',
                        'district': '',
                        'party': '',
                        'candidate': '',
                        'votes': ballots_cast,
                        'absentee': '',
                        'early_voting': '',
                        'election_day': ''
                    })
                    
                    precinct_added.add(current_precinct)
#                    print(f"Added precinct {current_precinct}: {registered_voters} registered, {ballots_cast} cast")
                else:
                    print(f"Skipping duplicate precinct {current_precinct}")
                continue
            
            # Check for office headers
            for pattern in office_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    print(f"Found office header: {line}")
                    current_office = line
                    district = ""
                    
                    district_match = re.search(r'District.*\s+(\d+)', line.title())
                    if district_match:
                        district = district_match.group(1)
                    elif 'Place' in line:
                        place_match = re.search(r'Place\s+(\d+)', line.title())
                        if place_match:
                            district = place_match.group(1)
                    #print(f"Found office: {current_office}")
                    else:
                        print(line)
            
            if current_office is None or current_precinct is None:
                continue
            
            # Skip header lines

            if ('Choice Party Absentee Voting' in line or
                'Not Assigned' in line or
                'Rejected write-in votes' in line or
                'Unresolved write-in votes' in line or
                'Contest Totals' in line):
                continue
            
            # Parse candidate lines
            candidate_pattern = r'^(.+?)\s+(REP|DEM|LIB|GRN|IND|\(W\))\s+([\d,]+)\s+[\d.]+%\s+([\d,]+)\s+[\d.]+%\s+([\d,]+)\s+[\d.]+%\s+([\d,]+)\s+[\d.]+%'
            candidate_match = re.match(candidate_pattern, line)
            
            if candidate_match:
                candidate_name = candidate_match.group(1).strip()
                party = candidate_match.group(2).strip()
                absentee = int(candidate_match.group(3).replace(',', ''))
                early = int(candidate_match.group(4).replace(',', ''))
                election_day = int(candidate_match.group(5).replace(',', ''))
                total = int(candidate_match.group(6).replace(',', ''))
                
                # Skip write-ins with actual names
                if '(W)' in party and len(candidate_name) > 10:
                    #print(f"Skipping write-in: {candidate_name}")
                    continue
                
                data.append({
                    'county': county,
                    'precinct': current_precinct,
                    'office': normalize_office_name(current_office),
                    'district': district,
                    'party': party,
                    'candidate': candidate_name,
                    'votes': total,
                    'absentee': absentee,
                    'early_voting': early,
                    'election_day': election_day
                })
#                print(f"Added: {candidate_name} ({party}) - {total} votes")
                continue

            # Skip Cast Votes lines
            if line.startswith('Cast Votes:'):
                continue
            
            # Handle Undervotes
            if line.startswith('Undervotes:'):
                vote_numbers = re.findall(r'\d+', line.replace('Undervotes:', ''))
                if len(vote_numbers) >= 4:
                    total = int(vote_numbers[3])
                    absentee = int(vote_numbers[0]) if len(vote_numbers) > 0 else 0
                    early = int(vote_numbers[1]) if len(vote_numbers) > 1 else 0
                    election_day = int(vote_numbers[2]) if len(vote_numbers) > 2 else 0
                    data.append({
                        'county': county,
                        'precinct': current_precinct,
                        'office': normalize_office_name(current_office),
                        'district': district,
                        'party': '',
                        'candidate': 'Under Votes',
                        'votes': total,
                        'absentee': absentee,
                        'early_voting': early,
                        'election_day': election_day
                    })
                continue
            
            # Handle Overvotes
            if line.startswith('Overvotes:'):
                vote_numbers = re.findall(r'\d+', line.replace('Overvotes:', ''))
                if len(vote_numbers) >= 4:
                    total = int(vote_numbers[3].replace(',', ''))
                    absentee = int(vote_numbers[0].replace(',', '')) if len(vote_numbers) > 0 else 0
                    early = int(vote_numbers[1].replace(',', '')) if len(vote_numbers) > 1 else 0
                    election_day = int(vote_numbers[2].replace(',', '')) if len(vote_numbers) > 2 else 0
                    data.append({
                        'county': county,
                        'precinct': current_precinct,
                        'office': normalize_office_name(current_office),
                        'district': district,
                        'party': '',
                        'candidate': 'Over Votes',
                        'votes': total,
                        'absentee': absentee,
                        'early_voting': early,
                        'election_day': election_day
                    })
                continue
        
        except Exception as e:
            print(f"Error on line {i}: {line[:50]}... - {e}")
            continue
    
    print(f"Processed {len(precinct_added)} precincts: {sorted(precinct_added)}")
    return data

def main():
    if len(sys.argv) != 4:
        print("Usage: python greenbox.py <input_pdf> <county_name> <output_csv>")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    county_name = sys.argv[2]
    output_csv = sys.argv[3]
    
    try:
        print(f"Extracting text from {input_pdf}...")
        text = extract_text_with_layout(input_pdf)
        
        print(f"Parsing election data for {county_name}...")
        data = parse_election_data(text, county_name)
        
        if not data:
            print("No data extracted.")
            return
        
        print(f"Writing {len(data)} records to {output_csv}...")
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['county', 'precinct', 'office', 'district', 'party', 'candidate', 'votes', 'absentee', 'early_voting', 'election_day']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        
        print(f"Success! Created {output_csv}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()