from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, PageTemplate, Frame, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfgen import canvas

def make_pdf(data, application_id):
    # Create the PDF document
    doc = SimpleDocTemplate(f"ysab_application_{application_id}.pdf", pagesize=letter, topMargin=20, bottomMargin=25, leftMargin=20, rightMargin=20)
    styles = getSampleStyleSheet()

    # Helper function for creating paragraph cells
    def create_paragraph_cell(text, style):
        if text is None or str(text).strip() == '':
            return ''
        return Paragraph(str(text), style)

    # Create a style for table cells with word wrap
    cell_style = styles["BodyText"]
    cell_style.wordWrap = 'CJK'

    # Create a function to add page numbers
    def add_page_number(canvas, doc):
        canvas.saveState()
        page_num = canvas.getPageNumber()
        text = f"{page_num}"
        canvas.drawRightString(letter[0] - 30, 15, text)  # 30 points from right, 15 from bottom
        canvas.restoreState()

    # Create page template with page numbers
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    template = PageTemplate(id='default', frames=frame, onPage=add_page_number)
    doc.addPageTemplates([template])

    # Create the elements for the report
    elements = []

    # Add the title
    elements.append(Paragraph("Dallas County Juror Fund Application", styles["Heading1"]))
    elements.append(Paragraph(" ", styles["BodyText"]))

    # Add application details
    application_details = [
        ["Application ID", data['_id']],
        ["Date", data["timestamp"]],
        ["Name", data["name"]],
        ["Title", data["app_title"]],
        ["Email", data["email"]],
        ["Phone", data["phone"]],
        ["Project Title", data["title"]],
        ["Service Area", data["service_area"]],
        ["Facility", data["facility"]],
        ["Address", data["address"]],
        ["Amount Requested", f"${data['amount']}"],
        ["Reporting Interval", data["reporting_interval"]],
        ["Other Funding", data["other_funding"]]
    ]

    # Modify the details table to wrap text
    details_table = Table(application_details, colWidths=[120, 350])
    details_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('WORDWRAP', (0,0), (-1,-1), True),
        ('TEXTCOLOR', (0,0), (0,-1), colors.white),
        ('BACKGROUND', (0,0), (0,-1), colors.blue),
    ]))
    elements.append(KeepTogether(details_table))
    elements.append(Paragraph(" ", styles["BodyText"]))

    # Problem Statement
    elements.append(Paragraph("Problem Statement", styles["Heading2"]))
    elements.append(Paragraph(data["problem_statement"], styles["BodyText"]))
    elements.append(Paragraph(" ", styles["BodyText"]))

    # Proposed Project
    elements.append(KeepTogether([
        Paragraph("Proposed Project", styles["Heading2"]),
        Paragraph("Target Group", styles["Heading3"]),
        Paragraph(data["target_group"], styles["BodyText"]),
        Paragraph(" ", styles["BodyText"])
    ]))
    elements.append(KeepTogether([
        Paragraph("Project Approach", styles["Heading3"]),
        Paragraph(data["project_approach"], styles["BodyText"]),
        Paragraph(" ", styles["BodyText"])
    ]))

    # Capacity Capabilities
    elements.append(KeepTogether([
        Paragraph("Capacity Capabilities", styles["Heading2"]),
        Paragraph(data["capacity_capabilities"], styles["BodyText"])
    ]))
    elements.append(Paragraph(" ", styles["BodyText"]))

    # Output and Outcome Measures
    output_heading = Paragraph("Output Measures", styles["Heading2"])

    # Output table with Paragraph wrapping
    output_data = [
        ["Outputs", "Target"],
        [data["output1"], data["target_output_1"]],
        [data["output2"], data["target_output_2"]],
        [data["output3"], data["target_output_3"]],
        [data["output4"], data["target_output_4"]],
        [data["output5"], data["target_output_5"]]
    ]

    # Convert each cell to a Paragraph for better word wrapping
    output_data = [
        [create_paragraph_cell(cell, cell_style) for cell in row]
        for row in output_data
    ]

    output_table = Table(output_data, colWidths=[300, 170])
    output_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightskyblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('FONTSIZE', (0,1), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.ghostwhite),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('WORDWRAP', (0,0), (-1,-1), True),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
    ]))
    elements.append(KeepTogether([output_heading, output_table]))
    elements.append(Paragraph(" ", styles["BodyText"]))

    # Outcome table with Paragraph wrapping
    outcome_heading = Paragraph("Outcome Measures", styles["Heading2"])

    outcome_data = [
        ["Outcomes", "Target"],
        [data["outcome1"], data["target_outcome_1"]],
        [data["outcome2"], data["target_outcome_2"]],
        [data["outcome3"], data["target_outcome_3"]],
        [data["outcome4"], data["target_outcome_4"]],
        [data["outcome5"], data["target_outcome_5"]]
    ]

    # Convert each cell to a Paragraph for better word wrapping
    outcome_data = [
        [create_paragraph_cell(cell, cell_style) for cell in row]
        for row in outcome_data
    ]

    outcome_table = Table(outcome_data, colWidths=[300, 170])
    outcome_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightskyblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('FONTSIZE', (0,1), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.ghostwhite),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('WORDWRAP', (0,0), (-1,-1), True),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
    ]))
    elements.append(KeepTogether([outcome_heading, outcome_table]))
    elements.append(Paragraph(" ", styles["BodyText"]))

    # Add the Goal Statement & Overall Impact
    elements.append(Paragraph("Goal Statement & Overall Impact", styles["Heading2"]))
    elements.append(Paragraph(data["project_goal_impact"], styles["BodyText"]))
    elements.append(Paragraph(" ", styles["BodyText"]))

    # Budget estimate table
    budget_heading = Paragraph("Budget Estimate", styles["Heading2"])

    # Convert budget data to use Paragraphs
    budget_data = [
        ["Category", "Description", "Cost", "Items", "Total"],
        [data["category1"], data["description1"], data["cost1"], data["items1"], data["total1"]],
        [data["category2"], data["description2"], data["cost2"], data["items2"], data["total2"]],
        [data["category3"], data["description3"], data["cost3"], data["items3"], data["total3"]],
        [data["category4"], data["description4"], data["cost4"], data["items4"], data["total4"]],
        [data["category5"], data["description5"], data["cost5"], data["items5"], data["total5"]],
        [data["category6"], data["description6"], data["cost6"], data["items6"], data["total6"]],
        [data["category7"], data["description7"], data["cost7"], data["items7"], data["total7"]]
    ]

    # Convert each cell to a Paragraph for better word wrapping
    budget_data = [
        [create_paragraph_cell(cell, cell_style) for cell in row]
        for row in budget_data
    ]

    budget_table = Table(budget_data, colWidths=[80, 220, 70, 70, 70])
    budget_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightskyblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('FONTSIZE', (0,1), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.ghostwhite),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('WORDWRAP', (0,0), (-1,-1), True),
        ('ALIGN', (0,1), (1,-1), 'LEFT'),    
        ('ALIGN', (2,1), (-1,-1), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))

    elements.append(KeepTogether([budget_heading, budget_table]))
    elements.append(Paragraph(" ", styles["BodyText"]))

    # budget cost breakdown
    budget_cost_breakdown_data = [
        ["Overall Project Cost:", f"${data['grandTotal']}"],
        ["Number of Youth Who Will Benefit:", data["youth_total"]],
        ["Individual Youth Benefit:", f"${data['benefit_per_youth']}"]
    ]

    budget_cost_breakdown_table = Table(budget_cost_breakdown_data, colWidths=[250, 200])
    budget_cost_breakdown_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('WORDWRAP', (0,0), (-1,-1), True),
        ('TEXTCOLOR', (0,0), (0,-1), colors.white),
        ('BACKGROUND', (0,0), (0,-1), colors.blue),
    ]))
    elements.append(KeepTogether(budget_cost_breakdown_table))
    elements.append(Paragraph(" ", styles["BodyText"]))

    # Build the PDF with page numbers
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)