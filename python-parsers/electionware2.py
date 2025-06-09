#!/usr/bin/env python3
"""
Jasper County PDF Election Data Extractor using pdfplumber
Adapted for November 5, 2024 General Election results
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
    if "President/Vice President" in office or "President and Vice President" in office:
        return "President"
    elif "US Senator" in office or "U.S. Senator" in office:
        return "U.S. Senate"
    elif "US Representative" in office or "U.S. Representative" in office:
        return "U.S. House"
    elif "State Representative" in office:
        return "State Representative"
    elif "Railroad Commissioner" in office:
        return "Railroad Commissioner"
    elif "Justice, Supreme Court" in office:
        return office
    elif "Judge," in office or "Justice," in office or "Presiding Judge" in office:
        return office
    elif "Member, State BoE" in office:
        return "State Board of Education"
    elif "Dist Attorney" in office or "District Attorney" in office:
        return "District Attorney"
    elif "County" in office:
        return office
    elif "Sheriff" in office:
        return "Sheriff"
    elif "Constable" in office:
        return office
    elif "Board of Trustees" in office or "Board of Trustee" in office:
        return office
    elif "Chief Justice" in office:
        return office
    elif "Dist Judge" in office:
        return office
    elif "Tax Rate Election" in office:
        return office
    elif "Proposition" in office:
        return office
    
    return office

def parse_election_data(text: str, county: str) -> List[Dict]:
    """Parse election data from PDF text with preserved layout."""
    data = []
    lines = text.split('\n')
    
    current_precinct = None
    current_office = None
    district = ""
    precinct_stats_added = set()
    
#    print(f"Processing {len(lines)} lines of text...")
    
    for i, line in enumerate(lines):
        try:
            original_line = line
            line = line.strip()
            if not line:
                continue
            
            # Check for precinct headers - format: "Pct # 1 Three Corners"
            if line.startswith("Pct #"):
                precinct_match = re.match(r'^Pct\s*#\s*(\d+)\s+(.+)$', line)
                if precinct_match:
                    precinct_num = precinct_match.group(1)
                    precinct_name = precinct_match.group(2)
                    current_precinct = f"Pct #{precinct_num} {precinct_name}"
                    print(f"Found precinct: {current_precinct}")
                    continue
            
            # Check for school district headers - format: "Buna ISD", "Evadale ISD", etc.
            if line.endswith(" ISD") or line.endswith(" CISD"):
                current_precinct = line
                #print(f"Found school district: {current_precinct}")
                continue
            
            # Check for other potential precinct/district headers that appear standalone
            # This catches sections that might be precinct names but don't follow the "Pct #" pattern
            if (len(line.split()) <= 4 and 
                not any(term in line.lower() for term in ['statistics', 'total', 'absentee', 'early', 'voting', 'day', 'vote for', 'overvotes', 'undervotes']) and
                not re.match(r'^(REP|DEM|LIB|GRN|IND)\s+', line) and
                not line.startswith(('For ', 'Against ')) and
                not re.match(r'^[A-Za-z].+?\s+\d+\s+\d+\s+\d+\s+\d+$', line) and
                current_precinct is None):
                # This might be a precinct header we missed
                current_precinct = line
                #print(f"Found potential precinct/district: {current_precinct}")
                continue
            
            # Skip if no current precinct
            if current_precinct is None:
                continue
            
            # Check for statistics section
            if line == "Statistics" or ("TOTAL" in line and "Absentee" in line and "Early" in line):
                continue
                
            # Parse registered voters - format: "Registered Voters - Total 57"
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
                    #print(f"Added registered voters: {registered_voters}")
                continue
            
            # Parse ballots cast - format: "Ballots Cast - Total 49 3 7 39"
            if "Ballots Cast - Total" in line:
                match = re.search(r'Ballots Cast - Total\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)', line)
                if match and f"{current_precinct}_ballots" not in precinct_stats_added:
                    total_ballots = int(match.group(1).replace(',', ''))
                    absentee = int(match.group(2).replace(',', ''))
                    early = int(match.group(3).replace(',', ''))
                    election_day = int(match.group(4).replace(',', ''))
                    
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
                    #print(f"Added ballots cast: {total_ballots}")
                continue
            
            # Parse blank ballots - format: "Ballots Cast - Blank 0 0 0 0"
            if "Ballots Cast - Blank" in line:
                match = re.search(r'Ballots Cast - Blank\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)', line)
                if match and f"{current_precinct}_blank" not in precinct_stats_added:
                    total_blank = int(match.group(1).replace(',', ''))
                    absentee_blank = int(match.group(2).replace(',', ''))
                    early_blank = int(match.group(3).replace(',', ''))
                    election_day_blank = int(match.group(4).replace(',', ''))
                    
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
                    #print(f"Added blank ballots: {total_blank}")
                continue
            
            # Parse overvotes - format: "Overvotes 0 0 0 0"
            if line.startswith("Overvotes") and current_office:
                match = re.search(r'Overvotes\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)', line)
                if match:
                    total_over = int(match.group(1).replace(',', ''))
                    absentee_over = int(match.group(2).replace(',', ''))
                    early_over = int(match.group(3).replace(',', ''))
                    election_day_over = int(match.group(4).replace(',', ''))
                    
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
                    #print(f"Added overvotes for {current_office}: {total_over}")
                continue
            
            # Parse undervotes - format: "Undervotes 1 0 1 0"  
            if line.startswith("Undervotes") and current_office:
                match = re.search(r'Undervotes\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)', line)
                if match:
                    total_under = int(match.group(1).replace(',', ''))
                    absentee_under = int(match.group(2).replace(',', ''))
                    early_under = int(match.group(3).replace(',', ''))
                    election_day_under = int(match.group(4).replace(',', ''))
                    
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
                    #print(f"Added undervotes for {current_office}: {total_under}")
                continue
            
            # Check for office headers
            office_indicators = [
                "President/Vice President", "US Senator", "U.S. Senator",
                "US Representative", "U.S. Representative", "Railroad Commissioner",
                "Justice, Supreme Court", "Justice,", "Judge,", "Presiding Judge",
                "Member, State BoE", "State Representative", "Dist Attorney",
                "County Attorney", "County Commissioner", "County Clerk", "County Tax",
                "Sheriff", "Constable", "Board of Trustees", "Board of Trustee", 
                "Chief Justice", "Dist Judge", "Tax Rate Election", "Proposition"
            ]
            
            # Check if this line contains an office indicator
            is_office_line = False
            for indicator in office_indicators:
                if indicator in line:
                    current_office = line
                    district = ""
                    
                    # Extract district number if present
                    district_match = re.search(r'Dist\s+(\d+)', line)
                    if district_match:
                        district = district_match.group(1)
                    elif re.search(r'Place\s+(\d+)', line):
                        place_match = re.search(r'Place\s+(\d+)', line)
                        if place_match:
                            district = place_match.group(1)
                    elif re.search(r'Pl\s+(\d+)', line):
                        pl_match = re.search(r'Pl\s+(\d+)', line)
                        if pl_match:
                            district = pl_match.group(1)
                    elif re.search(r'Pct\s+(\d+)', line):
                        pct_match = re.search(r'Pct\s+(\d+)', line)
                        if pct_match:
                            district = pct_match.group(1)
                    
                    print(f"Found office: {current_office}")
                    is_office_line = True
                    break
            
            if is_office_line:
                continue
            
            if current_office is None:
                continue
            
            # Skip header and summary lines
            skip_terms = [
                'Vote For', 'TOTAL', 'Absentee', 'Early', 'Election',
                'Voting', 'Day', 'Total Votes Cast', 
                'Not Assigned', 'Contest Totals', 'Write-In:', 'Voter Turnout'
            ]
            
            if any(skip_term in line for skip_term in skip_terms):
                continue
            
            # Parse candidate lines - format: "REP Donald J. Trump/JD Vance 42 3 6 33"
            candidate_pattern = r'^\s*(REP|DEM|LIB|GRN|IND)\s+(.+?)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)$'
            candidate_match = re.match(candidate_pattern, line)
            
            if candidate_match:
                print(f"Found candidate line: {line}")
                party = candidate_match.group(1).strip()
                candidate_name = candidate_match.group(2).strip()
                total = int(candidate_match.group(3).replace(',', ''))
                absentee = int(candidate_match.group(4).replace(',', ''))
                early = int(candidate_match.group(5).replace(',', ''))
                election_day = int(candidate_match.group(6).replace(',', ''))
                
                # Skip certain write-ins with actual names
                if candidate_name.startswith('Write-In:'):
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
                continue
            
            # Parse non-partisan candidates (school board, etc.)
            # Format: "Johnny Dale Gravis 651 6 553 92" or "William "Pete" Bond 905 15 693 197"
            nonpartisan_pattern = r'^([A-Za-z][^0-9]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$'
            nonpartisan_match = re.match(nonpartisan_pattern, line)
            
            if nonpartisan_match and current_office and ("Board" in current_office or "Proposition" in current_office):
                candidate_name = nonpartisan_match.group(1).strip()
                total = int(nonpartisan_match.group(2))
                absentee = int(nonpartisan_match.group(3))
                early = int(nonpartisan_match.group(4))
                election_day = int(nonpartisan_match.group(5))
                
                # Skip if this looks like a header or summary line
                if any(term in candidate_name.lower() for term in ['total', 'vote for', 'statistics', 'registered']):
                    continue
                
                data.append({
                    'county': county,
                    'precinct': current_precinct,
                    'office': normalize_office_name(current_office),
                    'district': district,
                    'party': '',
                    'candidate': candidate_name,
                    'votes': total,
                    'absentee': absentee,
                    'early_voting': early,
                    'election_day': election_day
                })
                print(f"Added non-partisan candidate: {candidate_name} - {total} votes")
                continue
            
            # Parse proposition votes (For/Against)
            if line.startswith(("For ", "Against ")) and current_office:
                prop_pattern = r'^(For|Against)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$'
                prop_match = re.match(prop_pattern, line)
                
                if prop_match:
                    position = prop_match.group(1)
                    total = int(prop_match.group(2))
                    absentee = int(prop_match.group(3))
                    early = int(prop_match.group(4))
                    election_day = int(prop_match.group(5))
                    
                    data.append({
                        'county': county,
                        'precinct': current_precinct,
                        'office': normalize_office_name(current_office),
                        'district': district,
                        'party': '',
                        'candidate': position,
                        'votes': total,
                        'absentee': absentee,
                        'early_voting': early,
                        'election_day': election_day
                    })
                    print(f"Added proposition vote: {position} - {total} votes")
                    continue
                    
        except Exception as e:
            print(f"Error processing line {i}: {original_line[:50]}... - {e}")
            continue
    
    print(f"Total records extracted: {len(data)}")
    return data

def main():
    if len(sys.argv) != 3:
        print("Usage: python jasper_county_parser.py <input_pdf> <output_csv>")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    output_csv = sys.argv[2]
    county_name = "Reeves"  # Fixed for this specific county
    
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