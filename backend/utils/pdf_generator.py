"""
Project: Fin Report - Documents team
Author: Dhinakaran Sekar
Email: dhinakaran.s@jubilantenterprises.in
Date: 2026-04-30 18:41
Description: Utility for processing Excel data and generating PDF reports using ReportLab.
"""

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os
import zipfile

def process_excel_to_pdfs(file_stream, output_dir):
    """
    Reads an Excel file, validates required columns, and generates categorized PDF reports.
    Returns a list of generated PDF file paths.
    """
    try:
        df = pd.read_excel(file_stream)
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {str(e)}")
        
    # Strip whitespace from column names for robust validation
    df.columns = [str(c).strip() for c in df.columns]

    required_columns = [
        'Branch', 'Loan Number', 'Loan Date', 'Customer Name', 'Dues', 'Due Amount',
        'Last Paid Date', 'Last Paid Amount', 'Next Installment Date', 'Frequency',
        'Consultant', 'Collection Executive', 'Installment Amount', 'Tenure',
        'No. Of Installments Received', 'Balance Installments', 'TDS AMOUNT'
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"The following required columns are missing in the Excel file: {', '.join(missing_columns)}")

    # Clean header mapping (case/space variations handled manually if needed, but exact matches required primarily)
    # The requirement specifically mentions: Loan Number -> Agreement No, Loan Date -> Agreement Date
    col_mapping = {
        'Loan Number': 'Agr. No.',
        'Loan Date': 'Agr. Date',
        'Next Installment Date': 'Next EMI Date',
        'Installment Amount': 'EMI Amount',
        'No. Of Installments Received': "No. Of EMI's Received",
        'Balance Installments': "Balance EMI's",
        'TDS AMOUNT': 'TDS Amount',
        'NOTE': 'Note',
        'note': 'Note',
        'Notes': 'Note',
        'NOTES': 'Note'
    }
    df.rename(columns=lambda x: col_mapping.get(str(x).strip(), str(x).strip()), inplace=True)
    
    # Add 'Diff' column across all reports: date difference between Next Installment Date and current date
    date_col = None
    for candidate in ['Next EMI Date', 'Next Installment Date']:
        if candidate in df.columns:
            date_col = candidate
            break
            
    if date_col:
        try:
            current_date = pd.Timestamp.now().normalize()
            try:
                parsed_dates = pd.to_datetime(df[date_col], errors='coerce', format='mixed', dayfirst=True)
            except (ValueError, TypeError):
                parsed_dates = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
                
            diff_days = (current_date - parsed_dates.dt.normalize()).dt.days
            diff_str = diff_days.apply(lambda x: str(int(round(x))) if pd.notna(x) else '-')
        except Exception:
            diff_str = '-'
            
        if 'Diff' in df.columns:
            df.drop('Diff', axis=1, inplace=True)
            
        idx = df.columns.get_loc(date_col) + 1
        df.insert(idx, 'Diff', diff_str)
        
    pdf_files = []
    
    styles = getSampleStyleSheet()
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        textColor=colors.whitesmoke,
        alignment=1, # Center
    )
    
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6,
        alignment=0, # Left
    )
    
    cell_style_right = ParagraphStyle(
        'CellStyleRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6,
        alignment=2, # Right
    )

    cell_style_center = ParagraphStyle(
        'CellStyleCenter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6,
        alignment=1, # Center
    )

    cell_style_total_red = ParagraphStyle(
        'CellStyleTotalRed',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        textColor=colors.red,
        alignment=1, # Center
    )

    cell_style_total_label = ParagraphStyle(
        'CellStyleTotalLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        textColor=colors.black,
        alignment=1, # Center
    )

    def generate_pdf(report_df, group_col, group_val, filename_prefix, secondary_cols=None):
        """
        Generates a single PDF report for a specific group (e.g., a specific Branch or Consultant).
        """
        if report_df.empty:
            return
            
        # Sort by Customer Name (alphabetical)
        if 'Customer Name' in report_df.columns:
            report_df.sort_values(by='Customer Name', ascending=True, inplace=True)
            
        # Remove the grouping column
        if group_col in report_df.columns:
            report_df.drop(group_col, axis=1, inplace=True)
            
        # Split by TDS Amount, Short Term, and Note (Most Delay Loans)
        tds_col = 'TDS Amount'
        tds_df = pd.DataFrame()
        short_term_df = pd.DataFrame()
        note_df = pd.DataFrame()
        main_df = report_df.copy()
        
        note_col = None
        for c in report_df.columns:
            if str(c).strip().lower() in ['note', 'notes']:
                note_col = c
                break

        is_tds = pd.Series(False, index=report_df.index)
        if tds_col in report_df.columns:
            is_tds = report_df[tds_col].astype(str).str.strip().str.lower().isin(['yes', 'y'])
            tds_df = report_df[is_tds].copy()

        is_short_term = pd.Series(False, index=report_df.index)
        if 'Customer Name' in report_df.columns:
            is_short_term = report_df['Customer Name'].astype(str).str.contains('short term', case=False, na=False) & (~is_tds)
            short_term_df = report_df[is_short_term].copy()

        is_note = pd.Series(False, index=report_df.index)
        if note_col:
            is_note = (report_df[note_col].astype(str).str.strip().str.lower().isin(['yes', 'y'])) & (~is_tds) & (~is_short_term)
            note_df = report_df[is_note].copy()

        # Sort Most Delay Loans List by Customer Name (ascending) and Diff (descending)
        if not note_df.empty:
            sort_cols = []
            ascending_order = []
            if 'Customer Name' in note_df.columns:
                note_df['_name_lower'] = note_df['Customer Name'].astype(str).str.strip().str.lower()
                sort_cols.append('_name_lower')
                ascending_order.append(True)
            if 'Diff' in note_df.columns:
                note_df['_diff_num'] = pd.to_numeric(note_df['Diff'], errors='coerce').fillna(-999999)
                sort_cols.append('_diff_num')
                ascending_order.append(False)
            if sort_cols:
                note_df.sort_values(by=sort_cols, ascending=ascending_order, inplace=True)
                for temp_col in ['_name_lower', '_diff_num']:
                    if temp_col in note_df.columns:
                        note_df.drop(temp_col, axis=1, inplace=True)

        # Sort Short Term Loan List by Customer Name (ascending) and Diff (descending)
        if not short_term_df.empty:
            sort_cols = []
            ascending_order = []
            if 'Customer Name' in short_term_df.columns:
                short_term_df['_name_lower'] = short_term_df['Customer Name'].astype(str).str.strip().str.lower()
                sort_cols.append('_name_lower')
                ascending_order.append(True)
            if 'Diff' in short_term_df.columns:
                short_term_df['_diff_num'] = pd.to_numeric(short_term_df['Diff'], errors='coerce').fillna(-999999)
                sort_cols.append('_diff_num')
                ascending_order.append(False)
            if sort_cols:
                short_term_df.sort_values(by=sort_cols, ascending=ascending_order, inplace=True)
                for temp_col in ['_name_lower', '_diff_num']:
                    if temp_col in short_term_df.columns:
                        short_term_df.drop(temp_col, axis=1, inplace=True)

        main_df = report_df[~is_tds & ~is_short_term & ~is_note].copy()

        # Remove Note column from output PDF
        if note_col:
            if note_col in report_df.columns:
                report_df.drop(note_col, axis=1, inplace=True)
            if note_col in main_df.columns:
                main_df.drop(note_col, axis=1, inplace=True)
            if note_col in short_term_df.columns:
                short_term_df.drop(note_col, axis=1, inplace=True)
            if note_col in tds_df.columns:
                tds_df.drop(note_col, axis=1, inplace=True)
            if note_col in note_df.columns:
                note_df.drop(note_col, axis=1, inplace=True)

        # Remove TDS Amount column from output PDF
        if tds_col:
            if tds_col in report_df.columns:
                report_df.drop(tds_col, axis=1, inplace=True)
            if tds_col in main_df.columns:
                main_df.drop(tds_col, axis=1, inplace=True)
            if tds_col in short_term_df.columns:
                short_term_df.drop(tds_col, axis=1, inplace=True)
            if tds_col in tds_df.columns:
                tds_df.drop(tds_col, axis=1, inplace=True)
            if tds_col in note_df.columns:
                note_df.drop(tds_col, axis=1, inplace=True)
            
        columns = report_df.columns.tolist()
        if not columns:
            return

        # Use safe group name for filename
        safe_group_val = "".join([c for c in str(group_val) if c.isalnum() or c in (' ', '-', '_')]).strip()
        if not safe_group_val:
            safe_group_val = "Unknown"
            
        category_dir = os.path.join(output_dir, filename_prefix)
        os.makedirs(category_dir, exist_ok=True)
            
        filename = f"{safe_group_val}.pdf".replace(" ", "_")
        filepath = os.path.join(category_dir, filename)
        
        # Generate A4 Landscape
        doc = SimpleDocTemplate(filepath, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        
        num_cols = len(columns)
        avail_width = landscape(A4)[0] - 40 # 20 margin left and right
        
        # Define fixed widths
        fixed_widths = {
            'Agr. No.': 45,
            'Dues': 30, 
            'Customer Name': 100, 
            'Due Amount': 55,
            'Tenure': 40,
            'No. Of EMI\'s Received': 45,
            'Balance EMI\'s': 45,
            'Diff': 30
        }
        total_fixed = sum(width for col, width in fixed_widths.items() if col in columns)
        fixed_count = sum(1 for col in fixed_widths if col in columns)
        
        if num_cols > fixed_count:
            other_width = (avail_width - total_fixed) / (num_cols - fixed_count)
        else:
            other_width = avail_width / num_cols
            
        col_widths = [fixed_widths.get(col, other_width) for col in columns]

        def create_table_from_df(df, display_cols, show_total=False, only_total=False, total_label="Total Amount", total_bg_color="#f0f0f0", highlight_dues=None):
            """
            Creates a ReportLab Table object from a DataFrame.
            """
            if highlight_dues is None:
                highlight_dues = True
                
            if df.empty and not only_total: return None
            data = []
            
            # Recalculate column widths for the display set
            local_avail_width = landscape(A4)[0] - 40
            local_num_cols = len(display_cols)
            local_total_fixed = sum(fixed_widths.get(c, 0) for c in display_cols)
            local_fixed_count = sum(1 for c in display_cols if c in fixed_widths)
            
            if local_num_cols > local_fixed_count:
                local_other_width = (local_avail_width - local_total_fixed) / (local_num_cols - local_fixed_count)
            else:
                local_other_width = local_avail_width / local_num_cols
            
            local_col_widths = [fixed_widths.get(c, local_other_width) for c in display_cols]

            # Header row
            if not only_total:
                data.append([Paragraph(str(col), header_style) for col in display_cols])
            
            # Data rows
            if not only_total:
                for _, row in df.iterrows():
                    row_data = []
                    for col in display_cols:
                        val = str(row[col]) if pd.notna(row[col]) else '-'
                        if val == '-':
                            row_data.append(Paragraph(val, cell_style_center))
                        elif col in ['Dues', 'Due Amount', 'Last Paid Amount', 'EMI Amount']:
                            row_data.append(Paragraph(val, cell_style_right))
                        elif col in ['Tenure', "No. Of EMI's Received", "Balance EMI's", 'Diff']:
                            row_data.append(Paragraph(val, cell_style_center))
                        else:
                            row_data.append(Paragraph(val, cell_style))
                    data.append(row_data)
            
            # Add Total row if requested
            if show_total and 'Due Amount' in display_cols:
                try:
                    total_val = pd.to_numeric(df['Due Amount'], errors='coerce').sum()
                    total_formatted = f"{total_val:,.1f}"
                except:
                    total_formatted = "0.0"
                    
                total_row = []
                due_col_idx = display_cols.index('Due Amount')
                for i, col in enumerate(display_cols):
                    if i == 0: # Place label in the first of the merged columns
                        total_row.append(Paragraph(total_label, cell_style_total_label))
                    elif i == due_col_idx:
                        total_row.append(Paragraph(total_formatted, cell_style_total_red))
                    else:
                        total_row.append(Paragraph("", cell_style))
                data.append(total_row)

            t = Table(data, colWidths=local_col_widths, repeatRows=1 if not only_total else 0)
            
            # Base style
            sc = []
            if not only_total:
                sc.extend([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, 0), 8),
                ])
            
            sc.extend([
                ('ALIGN', (0, 1 if not only_total else 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 1 if not only_total else 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#93999d'))
            ])
            
            # Special formatting for total row if it exists
            if show_total:
                total_row_idx = -1
                due_col_idx = display_cols.index('Due Amount') if 'Due Amount' in display_cols else 1
                sc.append(('LINEABOVE', (0, total_row_idx), (-1, total_row_idx), 1, colors.black))
                sc.append(('BACKGROUND', (0, total_row_idx), (-1, total_row_idx), colors.HexColor(total_bg_color)))
                sc.append(('SPAN', (0, total_row_idx), (max(0, due_col_idx - 1), total_row_idx))) # Merge columns before Due Amount
                sc.append(('ALIGN', (0, total_row_idx), (-1, total_row_idx), 'CENTER'))
                sc.append(('VALIGN', (0, total_row_idx), (-1, total_row_idx), 'MIDDLE'))
                sc.append(('TOPPADDING', (0, total_row_idx), (-1, total_row_idx), 10))
                sc.append(('BOTTOMPADDING', (0, total_row_idx), (-1, total_row_idx), 10))

            # Alternating row colors with dues > 1 highlighting if enabled
            if not only_total:
                row_count = len(data)
                for i in range(1, row_count):
                    if show_total and i == row_count - 1:
                        continue # Skip total row
                    
                    is_dues_gt_1 = False
                    if highlight_dues and 'Dues' in df.columns and (i - 1) < len(df):
                        try:
                            dues_raw = df.iloc[i - 1]['Dues']
                            if pd.notna(dues_raw):
                                dues_val = float(str(dues_raw).replace(',', '').strip())
                                if dues_val > 1:
                                    is_dues_gt_1 = True
                        except (ValueError, TypeError):
                            is_dues_gt_1 = False

                    if is_dues_gt_1:
                        bg_color = colors.HexColor('#fadbd8') # Soft red highlight for dues > 1
                    else:
                        bg_color = colors.HexColor('#ffffff') if i % 2 == 0 else colors.HexColor('#fbfbfb')
                    sc.append(('BACKGROUND', (0, i), (-1, i), bg_color))

                    # Apply bg color for Diff column if diff >= 10
                    if 'Diff' in df.columns and 'Diff' in display_cols and (i - 1) < len(df):
                        try:
                            diff_raw = df.iloc[i - 1]['Diff']
                            if pd.notna(diff_raw):
                                diff_val = float(str(diff_raw).replace(',', '').strip())
                                if diff_val >= 10:
                                    diff_col_idx = display_cols.index('Diff')
                                    sc.append(('BACKGROUND', (diff_col_idx, i), (diff_col_idx, i), colors.HexColor('#f4a09d')))
                        except (ValueError, TypeError):
                            pass
            
            t.setStyle(TableStyle(sc))
            return t

        elements = []
        # Main Title
        title_style = ParagraphStyle('Title', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, spaceAfter=15, alignment=1)
        elements.append(Paragraph(f"{filename_prefix} - {group_val}", title_style))
        
        # Style for nested group headers
        sub_group_header_style = ParagraphStyle(
            'SubGroupHeader', 
            parent=styles['Normal'], 
            fontName='Helvetica-Bold', 
            fontSize=9, 
            spaceBefore=15,
            spaceAfter=8, 
            textColor=colors.HexColor('#2980b9')
        )

        # Main List Table (Subdivided if secondary_cols provided)
        if not main_df.empty:
            if secondary_cols and all(col in main_df.columns for col in secondary_cols):
                # Ensure secondary columns have filled values for grouping
                for col in secondary_cols:
                    main_df[col] = main_df[col].fillna('Unknown')
                
                # Dynamic columns for the table (exclude grouping cols)
                table_cols = [c for c in columns if c not in secondary_cols]

                # Group and render sub-tables
                for sub_vals, sub_group in main_df.groupby(secondary_cols):
                    if isinstance(sub_vals, (list, tuple)):
                        sub_header_text = " | ".join([f"{col}: {val}" for col, val in zip(secondary_cols, sub_vals)])
                    else:
                        sub_header_text = f"{secondary_cols[0]}: {sub_vals}"
                    
                    # Group sub-header and table to keep them together across page breaks
                    sub_section = []
                    sub_section.append(Paragraph(sub_header_text, sub_group_header_style))
                    sub_section.append(create_table_from_df(sub_group, table_cols, show_total=True))
                    elements.append(KeepTogether(sub_section))
                
                # Add Grand Total for splitted tables
                elements.append(Spacer(1, 15))
                elements.append(create_table_from_df(main_df, table_cols, show_total=True, only_total=True, total_label="Grand Total", total_bg_color="#d6eaf8"))
            else:
                # Original single table behavior
                elements.append(create_table_from_df(main_df, columns, show_total=True))
            
        # Most Delay Loans List Table (Note column is YES)
        if not note_df.empty:
            note_section = []
            note_section.append(Spacer(1, 30))
            note_title_style = ParagraphStyle('NoteTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, spaceAfter=10, textColor=colors.black)
            note_section.append(Paragraph("MOST DELAY LOANS LIST", note_title_style))
            note_section.append(create_table_from_df(note_df, columns, show_total=False))
            elements.append(KeepTogether(note_section))

        # Short Term Loan List Table (Customer Name contains SHORT TERM)
        if not short_term_df.empty:
            short_term_section = []
            short_term_section.append(Spacer(1, 30))
            short_term_title_style = ParagraphStyle('ShortTermTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, spaceAfter=10, textColor=colors.black)
            short_term_section.append(Paragraph("SHORT TERM LOAN LIST", short_term_title_style))
            short_term_section.append(create_table_from_df(short_term_df, columns, show_total=False))
            elements.append(KeepTogether(short_term_section))

        # TDS List Table
        if not tds_df.empty:
            tds_section = []
            tds_section.append(Spacer(1, 30))
            tds_title_style = ParagraphStyle('TDSTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, spaceAfter=10, textColor=colors.black)
            tds_section.append(Paragraph("TDS LIST", tds_title_style))
            tds_section.append(create_table_from_df(tds_df, columns, show_total=False))
            elements.append(KeepTogether(tds_section))
            
        try:
            doc.build(elements)
            pdf_files.append(filepath)
        except Exception as e:
            print(f"Failed to build PDF {filename}: {e}")

    # Process all 3 reports
    col_exec_keys = [c for c in df.columns if 'Collection Executive' in c or 'collection executive' in c.lower()]
    exec_col = col_exec_keys[0] if col_exec_keys else None

    # 1. Branch Report
    if 'Branch' in df.columns:
        df_copy = df.copy()
        df_copy['Branch'] = df_copy['Branch'].fillna('Unknown')
        for val, group in df_copy.groupby('Branch'):
            secondary = []
            if exec_col in group.columns: secondary.append(exec_col)
            generate_pdf(group.copy(), 'Branch', val, 'Branch', secondary_cols=secondary)
            
    # 2. Consultant Report
    if 'Consultant' in df.columns:
        df_copy = df.copy()
        df_copy['Consultant'] = df_copy['Consultant'].fillna('Unknown')
        for val, group in df_copy.groupby('Consultant'):
            secondary = []
            if exec_col in group.columns: secondary.append(exec_col)
            generate_pdf(group.copy(), 'Consultant', val, 'Consultant', secondary_cols=secondary)
            
    # 3. Collection Executive Report
    if exec_col:
        df_copy = df.copy()
        df_copy[exec_col] = df_copy[exec_col].fillna('Unknown')
        for val, group in df_copy.groupby(exec_col):
            secondary = []
            if 'Consultant' in group.columns: secondary.append('Consultant')
            generate_pdf(group.copy(), exec_col, val, 'Collection_Executive', secondary_cols=secondary)
            
    return pdf_files

def create_zip_archive(pdf_files, output_path):
    """
    Compresses a list of PDF files into a single ZIP archive.
    """
    with zipfile.ZipFile(output_path, 'w') as zipf:
        for file in pdf_files:
            # File structure is <output_dir>/<Category>/<Filename>
            parts = os.path.split(file)
            category = os.path.basename(parts[0])
            arcname = os.path.join(category, parts[1])
            zipf.write(file, arcname)
    return output_path
