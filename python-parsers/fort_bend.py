#!/usr/bin/env python3
"""
Fort Bend County PDF Election Data Extractor using pdfplumber
Final production version with flexible precinct pattern support
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
    
    # Handle various President formats
    if "President" in office and ("Vice President" in office or "Vice-President" in office):
        return "President"
    elif "President/Vice-President" in office:
        return "President"
    elif "United States Senator" in office or "US Senator" in office or "U.S. Senator" in office:
        return "U.S. Senate"
    elif "United States Representative" in office or "US Representative" in office or "U.S. Representative" in office:
        return "U.S. House"
    elif "State Representative" in office:
        return "State Representative"
    elif "State Senator" in office:
        return "State Senate"
    elif "Railroad Commissioner" in office:
        return "Railroad Commissioner"
    elif "Justice, Supreme Court" in office:
        return office
    elif "Judge," in office or "Justice," in office or "Presiding Judge" in office:
        return office
    elif "Member, State Boe" in office:
        return "State Board of Education"
    elif "District Attorney" in office or "Dist Attorney" in office:
        return "District Attorney"
    elif "County" in office:
        return office
    elif "Sheriff" in office:
        return "Sheriff"
    elif "Constable" in office:
        return office
    elif "Board Of Trustees" in office:
        return office
    elif "Chief Justice" in office:
        return office
    
    return office

def parse_election_data(text: str, county: str) -> List[Dict]:
    """Parse election data from Fort Bend County PDF text with preserved layout."""
    data = []
    lines = text.split('\n')
    
    current_precinct = None
    current_office = None
    district = ""
    precinct_stats_added = set()
    
    print(f"Processing {len(lines)} lines of text...")
    
    i = 0
    while i < len(lines):
        try:
            original_line = lines[i]
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # Look for precinct pattern - can be "1004 - 1" or just "1006"
            precinct_match = re.match(r'^(\d+)(?:\s*-\s*(\d+))?$', line)
            if precinct_match:
                if precinct_match.group(2):  # Has sub-precinct
                    current_precinct = f"Precinct {precinct_match.group(1)}-{precinct_match.group(2)}"
                else:  # Just precinct number
                    current_precinct = f"Precinct {precinct_match.group(1)}"
                print(f"Found precinct: {current_precinct}")
                precinct_stats_added = set()  # Reset stats for new precinct
                i += 1
                continue
            
            # Skip if no current precinct
            if current_precinct is None:
                i += 1
                continue
            
            # Check for statistics section
            if line == "STATISTICS":
                i += 1
                continue
                
            # Parse registered voters - format: "Registered Voters - Total 3,788"
            if "Registered Voters - Total" in line:
                match = re.search(r'Registered Voters - Total\s+([\d,]+)', line)
                if match and f"{current_precinct}_registered" not in precinct_stats_added:
                    registered_voters = int(match.group(1).replace(',', ''))
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
                    precinct_stats_added.add(f"{current_precinct}_registered")
                    print(f"Added registered voters: {registered_voters}")
                i += 1
                continue
            
            # Parse ballots cast - format: "Ballots Cast - Total 2,584 332 104 2,148"
            # Note: Fort Bend format is Total, Election Day, Absentee, Early Voting
            if "Ballots Cast - Total" in line:
                match = re.search(r'Ballots Cast - Total\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)', line)
                if match and f"{current_precinct}_ballots" not in precinct_stats_added:
                    total_ballots = int(match.group(1).replace(',', ''))
                    election_day = int(match.group(2).replace(',', ''))
                    absentee = int(match.group(3).replace(',', ''))
                    early = int(match.group(4).replace(',', ''))
                    
                    data.append({
                        'county': county,
                        'precinct': current_precinct,
                        'office': 'Ballots Cast',
                        'district': '',
                        'party': '',
                        'candidate': '',
                        'votes': total_ballots,
                        'absentee': absentee,
                        'early_voting': early,
                        'election_day': election_day
                    })
                    precinct_stats_added.add(f"{current_precinct}_ballots")
                    print(f"Added ballots cast: {total_ballots}")
                i += 1
                continue
            
            # Parse blank ballots - format: "Ballots Cast - Blank 1 0 0 1"
            if "Ballots Cast - Blank" in line:
                match = re.search(r'Ballots Cast - Blank\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)', line)
                if match and f"{current_precinct}_blank" not in precinct_stats_added:
                    total_blank = int(match.group(1).replace(',', ''))
                    election_day_blank = int(match.group(2).replace(',', ''))
                    absentee_blank = int(match.group(3).replace(',', ''))
                    early_blank = int(match.group(4).replace(',', ''))
                    
                    data.append({
                        'county': county,
                        'precinct': current_precinct,
                        'office': 'Ballots Cast - Blank',
                        'district': '',
                        'party': '',
                        'candidate': '',
                        'votes': total_blank,
                        'absentee': absentee_blank,
                        'early_voting': early_blank,
                        'election_day': election_day_blank
                    })
                    precinct_stats_added.add(f"{current_precinct}_blank")
                    print(f"Added blank ballots: {total_blank}")
                i += 1
                continue
            
            # Parse overvotes - format: "Overvotes 0 0 0 0"
            if line.startswith("Overvotes") and current_office:
                match = re.search(r'Overvotes\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)', line)
                if match:
                    total_over = int(match.group(1).replace(',', ''))
                    election_day_over = int(match.group(2).replace(',', ''))
                    absentee_over = int(match.group(3).replace(',', ''))
                    early_over = int(match.group(4).replace(',', ''))
                    
                    data.append({
                        'county': county,
                        'precinct': current_precinct,
                        'office': normalize_office_name(current_office),
                        'district': district,
                        'party': '',
                        'candidate': 'Over Votes',
                        'votes': total_over,
                        'absentee': absentee_over,
                        'early_voting': early_over,
                        'election_day': election_day_over
                    })
                    print(f"Added overvotes for {current_office}: {total_over}")
                i += 1
                continue
            
            # Parse undervotes - format: "Undervotes 10 2 0 8"  
            if line.startswith("Undervotes") and current_office:
                match = re.search(r'Undervotes\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)', line)
                if match:
                    total_under = int(match.group(1).replace(',', ''))
                    election_day_under = int(match.group(2).replace(',', ''))
                    absentee_under = int(match.group(3).replace(',', ''))
                    early_under = int(match.group(4).replace(',', ''))
                    
                    data.append({
                        'county': county,
                        'precinct': current_precinct,
                        'office': normalize_office_name(current_office),
                        'district': district,
                        'party': '',
                        'candidate': 'Under Votes',
                        'votes': total_under,
                        'absentee': absentee_under,
                        'early_voting': early_under,
                        'election_day': election_day_under
                    })
                    print(f"Added undervotes for {current_office}: {total_under}")
                i += 1
                continue
            
            # Check for office headers
            office_indicators = [
                "President", "Vice-President", "United States Senator", "US Senator", "U.S. Senator",
                "United States Representative", "US Representative", "U.S. Representative", 
                "Railroad Commissioner", "Justice, Supreme Court", "Justice,", "Judge,", 
                "Presiding Judge", "Member, State BoE", "State Representative", "State Senator",
                "District Attorney", "Dist Attorney", "County Attorney", "County Commissioner", 
                "County Clerk", "County Tax", "Sheriff", "Constable", "Board of Trustees", 
                "Chief Justice", "Court of Appeals", "Judicial District"
            ]
            
            office_found = False
            for indicator in office_indicators:
                if indicator in line:
                    current_office = line
                    district = ""
                    office_found = True
                    
                    # Extract district number if present
                    district_match = re.search(r'District\s+(\d+)', line)
                    if district_match:
                        district = district_match.group(1)
                    elif re.search(r'Precinct\s+No\.\s+(\d+)', line):
                        precinct_match = re.search(r'Precinct\s+No\.\s+(\d+)', line)
                        if precinct_match:
                            district = precinct_match.group(1)
                    elif re.search(r'Place\s+(\d+)', line):
                        place_match = re.search(r'Place\s+(\d+)', line)
                        if place_match:
                            district = place_match.group(1)
                    
                    print(f"Found office: {current_office}")
                    break
            
            if office_found:
                i += 1
                continue
            
            # Parse Write-In Totals - format: "Write-In Totals 12 0.47% 3 0 9"
            if current_office and line.startswith("Write-In Totals"):
                # Extract numbers from Write-In Totals line
                parts = line.split()
                numbers = []
                for part in parts[2:]:  # Skip "Write-In" and "Totals"
                    if re.match(r'[\d,]+$', part):
                        numbers.append(int(part.replace(',', '')))
                
                if len(numbers) >= 4:
                    total = numbers[0]
                    election_day = numbers[1]
                    absentee = numbers[2]
                    early = numbers[3]
                    
                    data.append({
                        'county': county,
                        'precinct': current_precinct,
                        'office': normalize_office_name(current_office),
                        'district': district,
                        'party': '',
                        'candidate': 'Write-In Totals',
                        'votes': total,
                        'absentee': absentee,
                        'early_voting': early,
                        'election_day': election_day
                    })
                    print(f"Added Write-In Totals for {current_office}: {total} votes")
                i += 1
                continue
            
            # Skip header and summary lines
            skip_terms = [
                'Vote For', 'TOTAL', 'VOTE %', 'Absentee', 'Early', 'Election',
                'Voting', 'Day', 'Total Votes Cast', 'Not Assigned', 'Contest Totals', 
                'Write-In:', 'Voter Turnout'
            ]
            
            if any(skip_term in line for skip_term in skip_terms):
                i += 1
                continue
            
            # Parse candidate lines - Fort Bend format: "REP Donald J. Trump / JD Vance 1,526 59.29% 177 33 1,316"
            # Pattern: PARTY CANDIDATE_NAME TOTAL VOTE_PERCENT ELECTION_DAY ABSENTEE EARLY_VOTING
            if current_office and line.startswith(('REP', 'DEM', 'LIB', 'GRN', 'IND')):
                # Try flexible parsing to handle variations in spacing and formatting
                parts = line.split()
                if len(parts) >= 6:
                    party = parts[0]
                    
                    # Find where the numbers start by looking for the first number with commas or percentage
                    number_start = -1
                    for j, part in enumerate(parts[1:], 1):
                        if re.match(r'[\d,]+$', part) or '%' in part:
                            number_start = j
                            break
                    
                    if number_start > 1:
                        # Candidate name is everything from part 1 to number_start-1
                        candidate_name = ' '.join(parts[1:number_start])
                        
                        # Extract numbers (skip percentage if present)
                        numbers = []
                        for part in parts[number_start:]:
                            if re.match(r'[\d,]+$', part):
                                numbers.append(int(part.replace(',', '')))
                        
                        # Need at least 4 numbers: total, election_day, absentee, early
                        if len(numbers) >= 4:
                            total = numbers[0]
                            election_day = numbers[1]
                            absentee = numbers[2]
                            early = numbers[3]
                            
                            # Skip certain write-ins with actual names
                            if candidate_name.startswith('Write-In:'):
                                i += 1
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
                            print(f"Added candidate: {candidate_name} ({party}) - {total} votes")
                            
        except Exception as e:
            print(f"Error processing line {i}: {original_line[:50]}... - {e}")
            
        i += 1
    
    print(f"Total records extracted: {len(data)}")
    return data

def main():
    if len(sys.argv) != 4:
        print("Usage: python fort_bend_parser.py <input_pdf> <county_name> <output_csv>")
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
            print("No data extracted. Check the debug output above.")
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