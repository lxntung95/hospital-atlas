"""The README questions and the auth header, shared by the eval scripts."""

Q1 = "For major hip/knee replacement without complications (DRG 470), which five NY hospitals had the highest average total Medicare payment in 2024, and how do they compare with the NY and national averages?"
Q2 = "How does Montefiore compare with other Bronx hospitals on heart failure — Medicare payment, 30-day readmissions and mortality?"
Q3 = ["Which NY hospitals are the best?", "Hip and knee replacement in New York City, both cost and quality."]
MORE = ["What will I pay out of pocket for a knee replacement at NYU?", "Cheapest knee replacement in Boston?"]
CASES = [("Q1", [Q1]), ("Q2", [Q2]), ("Q3", Q3), ("More 1", [MORE[0]]), ("More 2", [MORE[1]])]


def auth_headers(token: str | None) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}
