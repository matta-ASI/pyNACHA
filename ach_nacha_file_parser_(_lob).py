# -*- coding: utf-8 -*-
"""ACH/NACHA File Parser (.lob)

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1SPUS0syTzB0C4RliLK2Nnt69Zx1uJYiM
"""

# ach_parser.py
import json

# Define field mappings for each record type based on NACHA specifications.
# Positions are 0-indexed for Python string slicing.
# (Length, Description)
RECORD_DEFINITIONS = {
    '1': {  # File Header Record
        'record_type_code': (0, 1, "Record Type Code"),
        'priority_code': (1, 3, "Priority Code"),
        'immediate_destination': (3, 13, "Immediate Destination"),
        'immediate_origin': (13, 23, "Immediate Origin"),
        'file_creation_date': (23, 29, "File Creation Date (YYMMDD)"),
        'file_creation_time': (29, 33, "File Creation Time (HHMM)"),
        'file_id_modifier': (33, 34, "File ID Modifier"),
        'record_size': (34, 37, "Record Size (must be 094)"),
        'blocking_factor': (37, 39, "Blocking Factor (must be 10)"),
        'format_code': (39, 40, "Format Code (must be 1)"),
        'immediate_destination_name': (40, 63, "Immediate Destination Name"),
        'immediate_origin_name': (63, 86, "Immediate Origin Name"),
        'reference_code': (86, 94, "Reference Code")
    },
    '5': {  # Batch Header Record
        'record_type_code': (0, 1, "Record Type Code"),
        'service_class_code': (1, 4, "Service Class Code (200=Mixed, 220=Credits, 225=Debits)"),
        'company_name': (4, 20, "Company Name"),
        'company_discretionary_data': (20, 40, "Company Discretionary Data"),
        'company_identification': (40, 50, "Company Identification (EIN or DDA)"),
        'standard_entry_class_code': (50, 53, "Standard Entry Class Code (e.g., PPD, CCD)"),
        'company_entry_description': (53, 63, "Company Entry Description"),
        'company_descriptive_date': (63, 69, "Company Descriptive Date (YYMMDD or other)"),
        'effective_entry_date': (69, 75, "Effective Entry Date (YYMMDD)"),
        'settlement_date_julian': (75, 78, "Settlement Date (Julian)"), # Inserted by ACH Operator
        'originator_status_code': (78, 79, "Originator Status Code (1=DFI)"),
        'originating_dfi_identification': (79, 87, "Originating DFI Identification (Routing Number)"),
        'batch_number': (87, 94, "Batch Number")
    },
    '6': {  # Entry Detail Record
        'record_type_code': (0, 1, "Record Type Code"),
        'transaction_code': (1, 3, "Transaction Code"),
        'receiving_dfi_identification': (3, 11, "Receiving DFI Identification (Routing Number, first 8 digits)"),
        'check_digit': (11, 12, "Check Digit (9th digit of routing number)"),
        'dfi_account_number': (12, 29, "DFI Account Number"),
        'amount': (29, 39, "Amount (cents)"),
        'individual_identification_number': (39, 54, "Individual Identification Number (Receiver ID)"),
        'individual_name': (54, 76, "Individual Name (Receiver Name)"),
        'discretionary_data': (76, 78, "Discretionary Data (Payment Type Code)"),
        'addenda_record_indicator': (78, 79, "Addenda Record Indicator (0=No, 1=Yes)"),
        'trace_number': (79, 94, "Trace Number")
    },
    '7': {  # Addenda Record
        'record_type_code': (0, 1, "Record Type Code"),
        'addenda_type_code': (1, 3, "Addenda Type Code (e.g., 05 for payment related)"),
        'payment_related_information': (3, 83, "Payment Related Information"),
        'addenda_sequence_number': (83, 87, "Addenda Sequence Number"),
        'entry_detail_sequence_number': (87, 94, "Entry Detail Sequence Number")
    },
    '8': {  # Batch Control Record
        'record_type_code': (0, 1, "Record Type Code"),
        'service_class_code': (1, 4, "Service Class Code (matches Batch Header)"),
        'entry_addenda_count': (4, 10, "Entry/Addenda Count"),
        'entry_hash': (10, 20, "Entry Hash (Sum of RDFI ID numbers)"),
        'total_debit_entry_dollar_amount': (20, 32, "Total Debit Entry Dollar Amount (cents)"),
        'total_credit_entry_dollar_amount': (32, 44, "Total Credit Entry Dollar Amount (cents)"),
        'company_identification': (44, 54, "Company Identification (matches Batch Header)"),
        'message_authentication_code': (54, 73, "Message Authentication Code (MAC)"), # Optional
        'reserved': (73, 79, "Reserved"),
        'originating_dfi_identification': (79, 87, "Originating DFI Identification (matches Batch Header)"),
        'batch_number': (87, 94, "Batch Number (matches Batch Header)")
    },
    '9': {  # File Control Record
        'record_type_code': (0, 1, "Record Type Code"),
        'batch_count': (1, 7, "Batch Count"),
        'block_count': (7, 13, "Block Count (lines/10, rounded up)"),
        'entry_addenda_count': (13, 21, "Entry/Addenda Count"),
        'entry_hash': (21, 31, "Entry Hash (Sum of Entry Hash totals from Batch Control)"),
        'total_debit_entry_dollar_amount_in_file': (31, 43, "Total Debit Entry Dollar Amount in File (cents)"),
        'total_credit_entry_dollar_amount_in_file': (43, 55, "Total Credit Entry Dollar Amount in File (cents)"),
        'reserved': (55, 94, "Reserved")
    }
}

def parse_record(line):
    """Parses a single 94-character ACH record."""
    if not line or len(line) < 1: # Basic check for empty or too short lines
        return None, None # Or raise an error

    record_type = line[0]
    definition = RECORD_DEFINITIONS.get(record_type)

    if not definition:
        # Handle unknown record types or '9' filled lines at the end of blocks
        if record_type == '9' and all(c == '9' for c in line): # Common filler
            return "filler", {"raw_line": line.strip()}
        print(f"Warning: Unknown or unhandled record type '{record_type}' for line: {line.strip()}")
        return "unknown", {"raw_line": line.strip()}

    parsed = {}
    for field_name, (start, end, description) in definition.items():
        # Ensure slicing does not go out of bounds if line is unexpectedly short
        # (though ACH lines should be 94 chars)
        value = line[start:min(end, len(line))].strip()
        parsed[field_name] = value
        # You might want to add type conversions here, e.g., for amounts, dates
        if field_name in ['amount', 'total_debit_entry_dollar_amount', 'total_credit_entry_dollar_amount',
                          'entry_addenda_count', 'entry_hash', 'batch_count', 'block_count',
                          'total_debit_entry_dollar_amount_in_file', 'total_credit_entry_dollar_amount_in_file']:
            try:
                # Amounts are in cents, usually integers. Hashes can be large.
                if 'amount' in field_name: # dollar amounts
                     parsed[field_name] = int(value) if value else 0
                elif 'hash' in field_name: # entry hashes
                     parsed[field_name] = int(value) if value else 0
                elif 'count' in field_name: # counts
                     parsed[field_name] = int(value) if value else 0

            except ValueError:
                # print(f"Warning: Could not convert field '{field_name}' value '{value}' to int.")
                pass # Keep as string if conversion fails, or handle error

    return record_type, parsed

def parse_ach_file_content(ach_content):
    """
    Parses the string content of an ACH file.
    The content can be a single string with newlines, or a list of lines.
    """
    ach_data = {
        "file_header": None,
        "batches": [],
        "file_control": None,
        "errors": [],
        "other_records": [] # For fillers or unknown types
    }
    current_batch = None
    current_entry = None

    # Handle if ach_content is a single block of text without newlines
    # or if it's already split into lines
    lines = []
    if isinstance(ach_content, str):
        if '\n' in ach_content:
            lines = ach_content.splitlines()
        else:
            # Assume it's a continuous block, split into 94-char chunks
            for i in range(0, len(ach_content), 94):
                lines.append(ach_content[i:i+94])
    elif isinstance(ach_content, list):
        lines = ach_content
    else:
        ach_data["errors"].append("Invalid ACH content type. Expected string or list of strings.")
        return ach_data


    for i, line in enumerate(lines):
        line_number = i + 1
        if len(line.strip()) == 0: # Skip empty lines
            continue
        if len(line) != 94 and not (line.startswith('9') and all(c == '9' for c in line.strip())): # Allow full filler lines
             # Allow lines shorter than 94 if they are filler lines (all '9's)
            is_filler_line_strict = all(c == '9' for c in line)
            if not is_filler_line_strict: # Only add error if not a pure filler line
                ach_data["errors"].append(f"Line {line_number}: Expected 94 characters, got {len(line)}. Content: '{line.strip()}'")
                # continue # Optionally skip malformed lines

        record_type, parsed_record = parse_record(line)

        if not parsed_record: # Error during parsing or empty line
            ach_data["errors"].append(f"Line {line_number}: Could not parse line. Content: '{line.strip()}'")
            continue

        if record_type == '1': # File Header
            ach_data['file_header'] = parsed_record
        elif record_type == '5': # Batch Header
            if current_batch: # Should not happen if file is well-formed
                ach_data["errors"].append(f"Line {line_number}: Unexpected Batch Header. Previous batch not closed.")
            current_batch = parsed_record
            current_batch['entries'] = []
            ach_data['batches'].append(current_batch)
        elif record_type == '6': # Entry Detail
            if not current_batch:
                ach_data["errors"].append(f"Line {line_number}: Entry Detail Record found outside of a batch.")
                continue
            current_entry = parsed_record
            current_entry['addenda'] = []
            current_batch['entries'].append(current_entry)
        elif record_type == '7': # Addenda
            if not current_entry:
                ach_data["errors"].append(f"Line {line_number}: Addenda Record found without a preceding Entry Detail.")
                continue
            # Link addenda to the last entry detail record
            # The trace number or sequence number in addenda should match the entry
            entry_detail_seq_from_addenda = parsed_record.get('entry_detail_sequence_number')
            if entry_detail_seq_from_addenda and current_entry.get('trace_number', '').endswith(entry_detail_seq_from_addenda):
                 current_entry['addenda'].append(parsed_record)
            else:
                # Fallback: if no current_entry or sequence numbers don't match specific logic,
                # try to find the correct entry in the current batch if possible, or log an error.
                # For simplicity here, we'll append to the last entry if it exists.
                # A more robust solution would match based on trace numbers.
                if current_batch and current_batch['entries']:
                    current_batch['entries'][-1]['addenda'].append(parsed_record)
                else:
                    ach_data["errors"].append(f"Line {line_number}: Could not associate Addenda with an Entry. Addenda: {parsed_record}")


        elif record_type == '8': # Batch Control
            if not current_batch:
                ach_data["errors"].append(f"Line {line_number}: Batch Control Record found outside of a batch context.")
                continue
            current_batch['batch_control'] = parsed_record
            current_batch = None # Reset for the next batch
            current_entry = None # Reset current entry as batch is closing
        elif record_type == '9': # File Control (or filler)
            if 'raw_line' in parsed_record and all(c == '9' for c in parsed_record['raw_line']):
                ach_data['other_records'].append({"type": "filler", "data": parsed_record})
            elif 'batch_count' in parsed_record: # It's a File Control record
                ach_data['file_control'] = parsed_record
                # End of file essentially
            else: # Should be the actual file control
                 ach_data['file_control'] = parsed_record

        elif record_type == "filler":
            ach_data['other_records'].append({"type": "filler", "data": parsed_record})
        elif record_type == "unknown":
            ach_data['other_records'].append({"type": "unknown", "data": parsed_record})
            ach_data["errors"].append(f"Line {line_number}: Encountered an unknown record type. Data: {parsed_record}")


    return ach_data

def parse_ach_lob_file(file_path):
    """
    Reads an ACH file (potentially from a .lob DB2 export containing raw ACH text)
    and parses its content.
    """
    try:
        # LOB files from DB2 might have specific encodings or could be binary.
        # For ACH, the content should be ASCII or EBCDIC.
        # We'll try reading as 'ascii' first, as NACHA is often ASCII.
        # If it's EBCDIC, you'd need to decode it (e.g., using 'cp037' or 'cp500').
        # This example assumes the .lob file contains plain text ACH data.
        with open(file_path, 'r', encoding='ascii', errors='ignore') as f:
            content = f.read()

        # If the LOB file might be EBCDIC, you could try:
        # with open(file_path, 'rb') as f_binary:
        #     raw_bytes = f_binary.read()
        # try:
        #     content = raw_bytes.decode('ascii')
        # except UnicodeDecodeError:
        #     print("File is not ASCII, trying EBCDIC (cp037)...")
        #     try:
        #         content = raw_bytes.decode('cp037') # Common EBCDIC codepage
        #     except UnicodeDecodeError:
        #         print("Failed to decode as ASCII or EBCDIC. The file might be binary or use a different encoding.")
        #         return {"errors": ["Failed to decode file content."]}


    except FileNotFoundError:
        return {"errors": [f"Error: File not found at {file_path}"]}
    except Exception as e:
        return {"errors": [f"Error reading file {file_path}: {e}"]}

    if not content.strip():
        return {"errors": [f"File {file_path} is empty or contains only whitespace."]}

    return parse_ach_file_content(content)

if __name__ == '__main__':
    # Create a dummy ACH file content for testing
    # This is a very simplified example. Real ACH files are more complex.
    dummy_ach_content = (
        "101100000001234567890BANK OF AMERICA TEST BANK         YYMMDDHHMM1094101DEST NAME              ORIGIN NAME            REF CODE\n"
        "5200COMPANY NAME      COMPANY DISCR DATA  1234567890PPDCOMPANY DESCRIP  YYMMDDYYMMDDJUL1ORIGIN_DFI_IDBATCH001\n"
        "632123456781ACCOUNTNUM12345   0000100000INDIVIDUAL ID  RECEIVER NAME         01TRACE_NUMBER_ENTRY_1\n"
        "705PAYMENT INFO FOR ENTRY 1                                                 0001TRACE_NUMBER_ENTRY_1\n"
        "637123456782ACCOUNTNUM67890   0000050000OTHER ID        OTHER NAME            00TRACE_NUMBER_ENTRY_2\n"
        "8200000003000000000000001500000000000000COMPANY ID  MAC                 ORIGIN_DFI_IDBATCH001\n"
        "90000010000010000000400000000000000000000150000                                           \n"
        "9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999\n" # Filler
    )

    # Simulate writing to a .lob file for the test
    test_lob_file = "test_ach_file.lob"
    # Replace YYMMDD and HHMM with actual date/time if needed for strict validation by some systems
    current_date = "240529" # Example: May 29, 2024
    current_time = "1200"   # Example: 12:00 PM
    dummy_ach_content = dummy_ach_content.replace("YYMMDD", current_date).replace("HHMM", current_time)
    dummy_ach_content = dummy_ach_content.replace("JUL", "150") # Example Julian date for settlement

    with open(test_lob_file, 'w', encoding='ascii') as f:
        f.write(dummy_ach_content)

    print(f"Attempting to parse: {test_lob_file}")
    parsed_data = parse_ach_lob_file(test_lob_file)

    if parsed_data.get("errors"):
        print("\nErrors encountered during parsing:")
        for error in parsed_data["errors"]:
            print(f"- {error}")

    print("\nParsed ACH Data:")
    # Pretty print the JSON structure
    print(json.dumps(parsed_data, indent=4))

    # Example: Accessing specific data
    if parsed_data.get("file_header"):
        print(f"\nFile Origin: {parsed_data['file_header'].get('immediate_origin_name')}")
    if parsed_data.get("batches") and parsed_data["batches"]:
        print(f"Number of batches: {len(parsed_data['batches'])}")
        first_batch = parsed_data['batches'][0]
        print(f"First batch company name: {first_batch.get('company_name')}")
        if first_batch.get('entries'):
            print(f"Number of entries in first batch: {len(first_batch['entries'])}")
            first_entry = first_batch['entries'][0]
            print(f"First entry amount: {first_entry.get('amount')} cents")
            if first_entry.get('addenda'):
                 print(f"First entry addenda info: {first_entry['addenda'][0].get('payment_related_information')}")

    # Clean up the dummy file
    import os
    os.remove(test_lob_file)