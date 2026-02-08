"""
Tax Calculator - Nigerian Tax Act 2025 Compliant
Calculates personal income tax, business tax, and applies reliefs
"""

from typing import Dict, List, Any

# Nigerian Tax Brackets 2025 (Personal Income Tax)
TAX_BRACKETS = [
    {"min": 0, "max": 300000, "rate": 0.07, "label": "First ₦300,000"},
    {"min": 300000, "max": 600000, "rate": 0.11, "label": "Next ₦300,000"},
    {"min": 600000, "max": 1100000, "rate": 0.15, "label": "Next ₦500,000"},
    {"min": 1100000, "max": 1600000, "rate": 0.19, "label": "Next ₦500,000"},
    {"min": 1600000, "max": 3200000, "rate": 0.21, "label": "Next ₦1,600,000"},
    {"min": 3200000, "max": float('inf'), "rate": 0.24, "label": "Above ₦3,200,000"}
]

# Relief Limits (Nigerian Tax Act 2025)
RELIEF_LIMITS = {
    "consolidated_relief": {
        "higher_of": ["20_percent_gross", "200000"],
        "max": 200000,
        "citation": "Tax Act 2025, Section 33"
    },
    "pension_contribution": {
        "max_percent": 0.08,  # 8% of gross income
        "citation": "Pension Reform Act 2014, Section 4"
    },
    "nhf_contribution": {
        "max_percent": 0.025,  # 2.5% of basic salary
        "citation": "National Housing Fund Act"
    },
    "nhis_contribution": {
        "max_percent": 0.05,  # 5% of basic salary
        "citation": "National Health Insurance Scheme Act"
    }
}


class TaxCalculator:
    """Nigerian Tax Calculator"""
    
    def __init__(self):
        self.tax_brackets = TAX_BRACKETS
        self.relief_limits = RELIEF_LIMITS
    
    def calculate_personal_income_tax(self, income_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate personal income tax based on Nigerian Tax Act 2025
        
        Args:
            income_data: {
                "employment_income": float,
                "business_income": float,
                "rental_income": float,
                "other_income": float,
                "pension_contribution": float,
                "nhf_contribution": float,
                "nhis_contribution": float
            }
        
        Returns:
            {
                "gross_income": float,
                "total_reliefs": float,
                "taxable_income": float,
                "tax_due": float,
                "breakdown": list,
                "citations": list
            }
        """
        # Calculate gross income
        gross_income = sum([
            income_data.get("employment_income", 0),
            income_data.get("business_income", 0),
            income_data.get("rental_income", 0),
            income_data.get("other_income", 0)
        ])
        
        # Calculate reliefs
        reliefs = self.calculate_reliefs(gross_income, income_data)
        total_reliefs = sum(r["amount"] for r in reliefs)
        
        # Calculate taxable income
        taxable_income = max(0, gross_income - total_reliefs)
        
        # Calculate tax using progressive brackets
        tax_breakdown = self.calculate_progressive_tax(taxable_income)
        tax_due = sum(b["tax"] for b in tax_breakdown)
        
        # Collect citations
        citations = [r["citation"] for r in reliefs if r.get("citation")]
        
        return {
            "gross_income": gross_income,
            "total_reliefs": total_reliefs,
            "taxable_income": taxable_income,
            "tax_due": tax_due,
            "breakdown": tax_breakdown,
            "reliefs": reliefs,
            "citations": citations
        }
    
    def calculate_reliefs(self, gross_income: float, income_data: Dict) -> List[Dict]:
        """Calculate all applicable reliefs"""
        reliefs = []
        
        # 1. Consolidated Relief (higher of 20% gross or ₦200,000)
        twenty_percent = gross_income * 0.20
        consolidated = max(twenty_percent, 200000)
        consolidated = min(consolidated, self.relief_limits["consolidated_relief"]["max"])
        
        reliefs.append({
            "name": "Consolidated Relief",
            "amount": consolidated,
            "citation": self.relief_limits["consolidated_relief"]["citation"]
        })
        
        # 2. Pension Contribution (8% of gross, if provided)
        pension = income_data.get("pension_contribution", 0)
        if pension > 0:
            max_pension = gross_income * self.relief_limits["pension_contribution"]["max_percent"]
            pension = min(pension, max_pension)
            reliefs.append({
                "name": "Pension Contribution",
                "amount": pension,
                "citation": self.relief_limits["pension_contribution"]["citation"]
            })
        
        # 3. NHF Contribution (2.5% of basic salary, if provided)
        nhf = income_data.get("nhf_contribution", 0)
        if nhf > 0:
            max_nhf = gross_income * self.relief_limits["nhf_contribution"]["max_percent"]
            nhf = min(nhf, max_nhf)
            reliefs.append({
                "name": "National Housing Fund",
                "amount": nhf,
                "citation": self.relief_limits["nhf_contribution"]["citation"]
            })
        
        # 4. NHIS Contribution (5% of basic salary, if provided)
        nhis = income_data.get("nhis_contribution", 0)
        if nhis > 0:
            max_nhis = gross_income * self.relief_limits["nhis_contribution"]["max_percent"]
            nhis = min(nhis, max_nhis)
            reliefs.append({
                "name": "Health Insurance",
                "amount": nhis,
                "citation": self.relief_limits["nhis_contribution"]["citation"]
            })
        
        return reliefs
    
    def calculate_progressive_tax(self, taxable_income: float) -> List[Dict]:
        """Calculate tax using progressive brackets"""
        breakdown = []
        remaining = taxable_income
        
        for bracket in self.tax_brackets:
            if remaining <= 0:
                break
            
            bracket_min = bracket["min"]
            bracket_max = bracket["max"]
            bracket_rate = bracket["rate"]
            
            # Calculate taxable amount in this bracket
            if remaining > (bracket_max - bracket_min):
                taxable_in_bracket = bracket_max - bracket_min
            else:
                taxable_in_bracket = remaining
            
            tax_in_bracket = taxable_in_bracket * bracket_rate
            
            breakdown.append({
                "bracket": bracket["label"],
                "rate": f"{bracket_rate * 100:.0f}%",
                "taxable_amount": taxable_in_bracket,
                "tax": tax_in_bracket
            })
            
            remaining -= taxable_in_bracket
        
        return breakdown
    
    def get_tax_bracket(self, taxable_income: float) -> Dict:
        """Get the highest tax bracket for given income"""
        for bracket in reversed(self.tax_brackets):
            if taxable_income >= bracket["min"]:
                return bracket
        return self.tax_brackets[0]
    
    def format_currency(self, amount: float) -> str:
        """Format amount as Nigerian Naira"""
        return f"₦ {amount:,.2f}"
