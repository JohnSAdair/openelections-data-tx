#!/usr/bin/env python3
"""
Collin County PDF Election Data Extractor using pdfplumber
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
    elif "United States Senator" in office or "U.S. Senator" in office:
        return "U.S. Senate"
    elif "United States Representative" in office or "U.S. Representative" in office:
        return "U.S. House"
    elif "State Representative" in office:
        return "State Representative"
    elif "State Senator" in office:
        return "State Senator"
    elif "Railroad Commissioner" in office:
        return "Railroad Commissioner"
    elif "Justice, Supreme Court" in office:
        return office
    elif "Judge," in office or "Justice," in office or "Presiding Judge" in office or "District Judge" in office:
        return office
    elif "Member, State Board of Education" in office or "Member, State BoE" in office:
        return "State Board of Education"
    elif "Chief Justice" in office:
        return office
    elif "County" in office:
        return office
    elif "Sheriff" in office:
        return "Sheriff"
    elif "Constable" in office:
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
    
    print(f"Processing {len(lines)} lines of text...")
    
    for i, line in enumerate(lines):
        try:
            original_line = line
            line = line.strip()
            if not line:
                continue
            
            # Check for precinct headers - format: "PCT 001", "PCT 002"
            if line.startswith("PCT "):
                precinct_match = re.match(r'^PCT\s+(\d+)$', line)
                if precinct_match:
                    precinct_num = precinct_match.group(1)
                    current_precinct = f"PCT {precinct_num}"
                    print(f"Found precinct: {current_precinct}")
                    continue
            
            # Skip if no current precinct
            if current_precinct is None:
                continue
            
            # Check for office headers - look for common office patterns
            office_indicators = [
                "President/Vice President", "United States Senator", "United States Representative",
                "Railroad Commissioner", "Justice, Supreme Court", "Presiding Judge", "Judge, Court of Criminal Appeals",
                "Member, State Board of Education", "State Senator", "State Representative",
                "Chief Justice", "Justice, 5th Court of Appeals", "District Judge", "Judge, County Probate Court",
                "Sheriff", "County Tax Assessor-Collector", "County Commissioner", "Constable", "Proposition"
            ]
            
            # Check if this line contains an office indicator
            is_office_line = False
            for indicator in office_indicators:
                if indicator in line and not any(skip_term in line for skip_term in ['Vote For', 'TOTAL', 'Rep ', 'Dem ', 'Lib ', 'Grn ', 'Write-In', 'YES', 'NO']):
                    current_office = line
                    district = ""
                    
                    # Extract district number if present
                    district_match = re.search(r'District\s+(\d+)', line)
                    if district_match:
                        district = district_match.group(1)
                    elif re.search(r'Place\s+(\d+)', line):
                        place_match = re.search(r'Place\s+(\d+)', line)
                        if place_match:
                            district = place_match.group(1)
                    elif re.search(r'Precinct\s+No\.\s+(\d+)', line):
                        prec_match = re.search(r'Precinct\s+No\.\s+(\d+)', line)
                        if prec_match:
                            district = prec_match.group(1)
                    
                    print(f"Found office: {current_office}")
                    is_office_line = True
                    break
            
            if is_office_line:
                continue
            
            if current_office is None:
                continue
            
            # Debug: Show all lines when processing President office
            if current_office and "President" in current_office:
                print(f"[PRESIDENT] Processing line: '{line}'")
            
            # Skip header and summary lines
            skip_terms = [
                'Vote For', 'TOTAL', 'VOTE %', 'Election Day', 'Early Voting',
                'Ballot by mail', 'Provisional', 'Limited', 'Contest Totals'
            ]
            
            # Use more precise matching to avoid false positives
            is_skip_line = False
            for skip_term in skip_terms:
                if skip_term in line:
                    is_skip_line = True
                    break
            
            if is_skip_line:
                if current_office and "President" in current_office:
                    print(f"[PRESIDENT] Skipping header/summary line: '{line}'")
                continue
            
            # Parse overvotes - format: "Overvotes 0 0 0 0 0 0"
            if line.startswith("Overvotes") and current_office:
                # Extract numbers from the line
                numbers = re.findall(r'\d+', line)
                if len(numbers) >= 6:
                    total_over = int(numbers[0])
                    election_day = int(numbers[1])
                    early_voting = int(numbers[2])
                    ballot_by_mail = int(numbers[3])
                    provisional = int(numbers[4])
                    limited = int(numbers[5])
                    
                    data.append({
                        'county': county,
                        'precinct': current_precinct,
                        'office': normalize_office_name(current_office),
                        'district': district,
                        'party': '',
                        'candidate': 'Over Votes',
                        'votes': total_over,
                        'election_day': election_day,
                        'early_voting': early_voting,
                        'ballot_by_mail': ballot_by_mail,
                        'provisional': provisional,
                        'limited': limited
                    })
                    print(f"Added overvotes for {current_office}: {total_over}")
                continue
            
            # Parse undervotes - format: "Undervotes 10 2 8 0 0 0"
            if line.startswith("Undervotes") and current_office:
                numbers = re.findall(r'\d+', line)
                if len(numbers) >= 6:
                    total_under = int(numbers[0])
                    election_day = int(numbers[1])
                    early_voting = int(numbers[2])
                    ballot_by_mail = int(numbers[3])
                    provisional = int(numbers[4])
                    limited = int(numbers[5])
                    
                    data.append({
                        'county': county,
                        'precinct': current_precinct,
                        'office': normalize_office_name(current_office),
                        'district': district,
                        'party': '',
                        'candidate': 'Under Votes',
                        'votes': total_under,
                        'election_day': election_day,
                        'early_voting': early_voting,
                        'ballot_by_mail': ballot_by_mail,
                        'provisional': provisional,
                        'limited': limited
                    })
                    print(f"Added undervotes for {current_office}: {total_under}")
                continue
            
            # Parse candidate lines - format: "Rep Donald J. Trump/JD Vance 1,036 54.07% 119 886 30 1 0"
            # More flexible pattern to handle various number formats and spacing
            candidate_pattern = r'^\s*(Rep|Dem|Lib|Grn|IND)\s+(.+?)\s+([\d,]+)\s+[\d.]+%\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)'
            candidate_match = re.search(candidate_pattern, line)
            
            # Debug: Check if line looks like a candidate line but doesn't match
            if line.startswith(('Rep ', 'Dem ', 'Lib ', 'Grn ', 'IND ')) and current_office:
                print(f"Checking candidate line: '{line}'")
                if candidate_match:
                    print(f"✓ Matched candidate pattern")
                else:
                    print(f"✗ Did not match candidate pattern")
                    # Try to extract numbers manually for debugging
                    numbers = re.findall(r'[\d,]+', line)
                    print(f"  Numbers found: {numbers}")
                    print(f"  Line length: {len(line)}")
                    print(f"  Line repr: {repr(line)}")
                    
                    # Try a simpler pattern that's more forgiving
                    simple_pattern = r'(Rep|Dem|Lib|Grn|IND)\s+(.+)'
                    simple_match = re.match(simple_pattern, line)
                    if simple_match:
                        print(f"  Simple pattern matched - Party: '{simple_match.group(1)}', Rest: '{simple_match.group(2)}'")
                        
                        # Try to parse the numbers from the rest of the line
                        rest = simple_match.group(2)
                        numbers = re.findall(r'[\d,]+', rest)
                        if len(numbers) >= 6:
                            try:
                                # Extract candidate name - everything before the first number
                                first_num_pos = rest.find(numbers[0])
                                candidate_name = rest[:first_num_pos].strip()
                                
                                party = simple_match.group(1)
                                total = int(numbers[0].replace(',', ''))
                                # Skip percentage, take next 5 numbers
                                election_day = int(numbers[2].replace(',', '')) if len(numbers) > 2 else 0
                                early_voting = int(numbers[3].replace(',', '')) if len(numbers) > 3 else 0
                                ballot_by_mail = int(numbers[4].replace(',', '')) if len(numbers) > 4 else 0
                                provisional = int(numbers[5].replace(',', '')) if len(numbers) > 5 else 0
                                limited = int(numbers[6].replace(',', '')) if len(numbers) > 6 else 0
                                
                                # Handle Write-In Totals
                                if candidate_name.startswith('Write-In'):
                                    candidate_name = 'Write-In Totals'
                                
                                data.append({
                                    'county': county,
                                    'precinct': current_precinct,
                                    'office': normalize_office_name(current_office),
                                    'district': district,
                                    'party': party,
                                    'candidate': candidate_name,
                                    'votes': total,
                                    'election_day': election_day,
                                    'early_voting': early_voting,
                                    'ballot_by_mail': ballot_by_mail,
                                    'provisional': provisional,
                                    'limited': limited
                                })
                                print(f"Added candidate (simple fallback): {candidate_name} ({party}) - {total} votes")
                                continue
                            except (ValueError, IndexError) as e:
                                print(f"  Simple fallback parsing failed: {e}")
                    
                    # Try alternative parsing if we have enough numbers
                    if len(numbers) >= 6:
                        parts = line.split()
                        if len(parts) >= 8:
                            try:
                                party = parts[0]
                                # Find where the percentage is (ends with %)
                                pct_idx = -1
                                for idx, part in enumerate(parts):
                                    if part.endswith('%'):
                                        pct_idx = idx
                                        break
                                
                                if pct_idx > 0:
                                    candidate_name = ' '.join(parts[1:pct_idx-1])  # Everything between party and total votes
                                    total = int(parts[pct_idx-1].replace(',', ''))
                                    election_day = int(parts[pct_idx+1].replace(',', ''))
                                    early_voting = int(parts[pct_idx+2].replace(',', ''))
                                    ballot_by_mail = int(parts[pct_idx+3].replace(',', ''))
                                    provisional = int(parts[pct_idx+4].replace(',', ''))
                                    limited = int(parts[pct_idx+5].replace(',', ''))
                                    
                                    # Handle Write-In Totals
                                    if candidate_name.startswith('Write-In'):
                                        candidate_name = 'Write-In Totals'
                                    
                                    data.append({
                                        'county': county,
                                        'precinct': current_precinct,
                                        'office': normalize_office_name(current_office),
                                        'district': district,
                                        'party': party,
                                        'candidate': candidate_name,
                                        'votes': total,
                                        'election_day': election_day,
                                        'early_voting': early_voting,
                                        'ballot_by_mail': ballot_by_mail,
                                        'provisional': provisional,
                                        'limited': limited
                                    })
                                    print(f"Added candidate (percentage fallback): {candidate_name} ({party}) - {total} votes")
                                    continue
                            except (ValueError, IndexError) as e:
                                print(f"  Percentage fallback parsing failed: {e}")
            
            if candidate_match:
                print(f"Found candidate line: {line}")
                party = candidate_match.group(1).strip()
                candidate_name = candidate_match.group(2).strip()
                total = int(candidate_match.group(3).replace(',', ''))
                election_day = int(candidate_match.group(4).replace(',', ''))
                early_voting = int(candidate_match.group(5).replace(',', ''))
                ballot_by_mail = int(candidate_match.group(6).replace(',', ''))
                provisional = int(candidate_match.group(7).replace(',', ''))
                limited = int(candidate_match.group(8).replace(',', ''))
                
                # Handle Write-In Totals
                if candidate_name.startswith('Write-In'):
                    candidate_name = 'Write-In Totals'
                
                data.append({
                    'county': county,
                    'precinct': current_precinct,
                    'office': normalize_office_name(current_office),
                    'district': district,
                    'party': party,
                    'candidate': candidate_name,
                    'votes': total,
                    'election_day': election_day,
                    'early_voting': early_voting,
                    'ballot_by_mail': ballot_by_mail,
                    'provisional': provisional,
                    'limited': limited
                })
                print(f"Added candidate: {candidate_name} ({party}) - {total} votes")
                continue
            
            # Parse non-partisan candidates (for uncontested races)
            # Format: "Rep Angela Tucker 1,190 100.00% 143 1,014 30 3 0"
            uncontested_pattern = r'^\s*(Rep|Dem)\s+(.+?)\s+([\d,]+)\s+100\.00%\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)$'
            uncontested_match = re.match(uncontested_pattern, line)
            
            if uncontested_match and current_office:
                party = uncontested_match.group(1).strip()
                candidate_name = uncontested_match.group(2).strip()
                total = int(uncontested_match.group(3).replace(',', ''))
                election_day = int(uncontested_match.group(4).replace(',', ''))
                early_voting = int(uncontested_match.group(5).replace(',', ''))
                ballot_by_mail = int(uncontested_match.group(6).replace(',', ''))
                provisional = int(uncontested_match.group(7).replace(',', ''))
                limited = int(uncontested_match.group(8).replace(',', ''))
                
                data.append({
                    'county': county,
                    'precinct': current_precinct,
                    'office': normalize_office_name(current_office),
                    'district': district,
                    'party': party,
                    'candidate': candidate_name,
                    'votes': total,
                    'election_day': election_day,
                    'early_voting': early_voting,
                    'ballot_by_mail': ballot_by_mail,
                    'provisional': provisional,
                    'limited': limited
                })
                print(f"Added uncontested candidate: {candidate_name} ({party}) - {total} votes")
                continue
            
            # Parse proposition votes (YES/NO)
            prop_pattern = r'^\s*(YES|NO)\s+([\d,]+)\s+[\d.]+%\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)$'
            prop_match = re.match(prop_pattern, line)
            
            if prop_match and current_office and "Proposition" in current_office:
                position = prop_match.group(1)
                total = int(prop_match.group(2).replace(',', ''))
                election_day = int(prop_match.group(3).replace(',', ''))
                early_voting = int(prop_match.group(4).replace(',', ''))
                ballot_by_mail = int(prop_match.group(5).replace(',', ''))
                provisional = int(prop_match.group(6).replace(',', ''))
                limited = int(prop_match.group(7).replace(',', ''))
                
                data.append({
                    'county': county,
                    'precinct': current_precinct,
                    'office': normalize_office_name(current_office),
                    'district': district,
                    'party': '',
                    'candidate': position,
                    'votes': total,
                    'election_day': election_day,
                    'early_voting': early_voting,
                    'ballot_by_mail': ballot_by_mail,
                    'provisional': provisional,
                    'limited': limited
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
        print("Usage: python collin_county_parser.py <input_pdf> <output_csv>")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    output_csv = sys.argv[2]
    county_name = "Collin"  # Fixed for this specific county
    
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
            fieldnames = ['county', 'precinct', 'office', 'district', 'party', 'candidate', 'votes', 'election_day', 'early_voting', 'ballot_by_mail', 'provisional', 'limited']
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