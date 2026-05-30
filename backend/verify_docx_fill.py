import os
from utils.promissory_generator import fill_promissory_note_docx

def main():
    print("Testing docx fill...")
    template_path = os.path.abspath("template/Promissory Note.docx")
    output_path = os.path.abspath("test_filled_promissory.docx")
    
    form_data = {
        'loanAmount': '500000',
        'place': 'Kottayam',
        'loanDate': '2026-05-17',
        'companyName': 'Thalakkulam Enterprises',
        'companyAddress': 'No. 10/138, Thalakkulam Building, Mutholy, Kottayam - 686573, Kerala.',
        'proprietorName': 'Mrs. Alen Sebastian',
        'fatherOfProprietor': 'Sebastian Jacob',
        'lenderName': 'Jubilant Enterprises Private Limited',
        'repayment': '15000',
        'interest': '18.50'
    }
    
    joinees_list = [
        {'name': 'Sri. Robin Thomas', 'father': 'Thomas Jacob', 'address': 'Kottayam'}
    ]
    
    fill_promissory_note_docx(form_data, joinees_list, template_path, output_path)
    print(f"Success! Filled file saved to: {output_path}")
    
    # Assert font settings
    import docx
    check_doc = docx.Document(output_path)
    print("\nVerifying output font name and size:")
    all_calibri_14 = True
    for idx, p in enumerate(check_doc.paragraphs):
        for run in p.runs:
            # Note: run.font.size returns Pt(14) which is a float/Pt subclass
            if run.font.name != 'Calibri' or run.font.size.pt != 14.0:
                print(f"Mismatch in Paragraph {idx}: Text='{run.text}' | Font={run.font.name} | Size={run.font.size}")
                all_calibri_14 = False
                
    if all_calibri_14:
        print("Confirmed: 100% of runs are successfully set to Calibri 14pt!")
    else:
        print("Warning: Some runs were not Calibri 14pt.")

if __name__ == "__main__":
    main()
