"""Fill the official evidence template using audited cell bindings."""
from WenShu.exact_template_fill import fill_evidence

def generate_ELdocx(data, template_docx):
    return fill_evidence(data, template_docx)
