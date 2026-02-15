import math
from datetime import date

import streamlit as st


DEFAULT_LOOKUP_VALUES = {
    "STRESS_FACTOR": 0.85,
    "DSCR_TARGET": 1.3,
    "CASHFLOW_DEFICIT_REPAY_SHARE_MAX": 0.5,
    "LTV_MAX_MOVABLE": 1.25,
    "LTV_MAX_IMMOVABLE": 1.1,
    "EQUITY_MIN_RATIO": 0.1,
    "DATA_VARIANCE_MAX": 0.2,
    "BUSINESS_AGE_MIN": 6.0,
    "AGE_MAX": 99.0,
    "BRANCH_APPROVAL_LIMIT_ETB": 50000.0,
    "BUSINESS_LOAN_HARD_MAX_ETB": 3000000.0,
    "W_CHARACTER": 30.0,
    "W_CAPACITY": 39.0,
    "W_CAPITAL": 10.0,
    "W_COLLATERAL": 10.0,
    "W_CONDITION": 10.0,
}

DEFAULT_SECTOR_STRESS = {
    "Trade": 0.85,
    "Service": 0.8,
    "Manufacturing": 0.7,
    "Agriculture": 0.6,
    "Other": 0.55,
}

CUSTOMER_INPUT_DEFAULTS = {
    "credit_officer_id": "CO-001",
    "credit_officer_name": "Sample Officer",
    "applicant_name": "Sample Applicant",
    "applicant_id": "APP-0001",
    "sex": "M",
    "age_years": "35",
    "marital_status": "Married",
    "literacy": "Secondary/High School",
    "repeat_borrower": "No",
    "loan_series": "2",
    "prior_default": "No",
    "branch": "Head Office",
    "requested_loan_amount": "50000",
    "monthly_installment_override": "4584",
    "term_months": "12",
    "annual_interest_rate": "18",
    "business_name": "Sample Business",
    "ownership": "Sole Proprietor",
    "site_visit_assessment": 3,
    "sector": "Trade",
    "training_certification": "Yes",
    "is_business_seasonal": "No",
    "business_type": "Retail / Trading",
    "years_in_business_months": "24",
    "character_references": "Good",
    "loan_purpose": "Working Capital",
    "stability_months": "24",
    "stated_revenue": "30000",
    "verified_revenue": "28000",
    "cogs_inventory": "12000",
    "other_monthly_income": "2000",
    "rent": "3000",
    "household_expenses": "5000",
    "utilities": "800",
    "owner_withdrawals": "1500",
    "wages": "2500",
    "transport": "700",
    "other_operating_costs": "1000",
    "total_capital": "20000",
    "additional_savings_equity": "10000",
    "collateral_type": "Movable",
    "collateral_insured": "Yes",
    "market_value": "150000",
}

CUSTOMER_DEFAULTS_VERSION = 4

RISK_BANDS = [
    (85, "Very Low Risk"),
    (70, "Low Risk"),
    (55, "Moderate Risk"),
    (40, "High Risk"),
    (1, "Very High Risk"),
]


def init_state() -> None:
    if "lookup_values" not in st.session_state:
        st.session_state.lookup_values = DEFAULT_LOOKUP_VALUES.copy()
    if "sector_stress" not in st.session_state:
        st.session_state.sector_stress = DEFAULT_SECTOR_STRESS.copy()
    if st.session_state.get("customer_defaults_version", 0) < CUSTOMER_DEFAULTS_VERSION:
        for key, value in CUSTOMER_INPUT_DEFAULTS.items():
            st.session_state[key] = value
        st.session_state.application_date = date.today()
        st.session_state.customer_defaults_version = CUSTOMER_DEFAULTS_VERSION


def reset_customer_defaults():
    for key, value in CUSTOMER_INPUT_DEFAULTS.items():
        st.session_state[key] = value
    st.session_state.application_date = date.today()
    st.session_state.scorecard_step = 1


def parse_optional_float(raw_value: str):
    cleaned = raw_value.replace(",", "").strip()
    if cleaned == "":
        return None, None
    try:
        return float(cleaned), None
    except ValueError:
        return None, "Enter a valid number."


def optional_number(label: str, key: str, help_text: str = ""):
    raw_value = st.text_input(label, key=key, help=help_text)
    parsed_value, error = parse_optional_float(raw_value)
    if error:
        st.error(f"{label}: {error}")
    return parsed_value


def pmt(rate: float, periods: float, present_value: float):
    if rate == 0:
        if periods == 0:
            return None
        return present_value / periods
    if periods == 0:
        return None
    return (rate * present_value) / (1 - math.pow(1 + rate, -periods))


def safe_divide(numerator, denominator):
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def risk_band(score: float) -> str:
    for threshold, band in RISK_BANDS:
        if score >= threshold:
            return band
    return "Very High Risk"


def format_number(value, decimals=2):
    if value is None:
        return "-"
    return f"{value:,.{decimals}f}"


def calculate_scorecard(inputs, lookups, sector_stress):
    sector = inputs["sector"]
    stress_factor = sector_stress.get(sector) if sector else None

    monthly_installment_used = inputs["monthly_installment_override"]
    if monthly_installment_used is None:
        if (
            inputs["requested_loan_amount"] is not None
            and inputs["term_months"] is not None
            and inputs["annual_interest_rate"] is not None
        ):
            monthly_rate = (inputs["annual_interest_rate"] / 100) / 12
            monthly_installment_used = pmt(
                monthly_rate,
                inputs["term_months"],
                inputs["requested_loan_amount"],
            )

    total_operating_expenses = None
    if all(
        x is not None
        for x in [
            inputs["rent"],
            inputs["utilities"],
            inputs["wages"],
            inputs["transport"],
            inputs["other_operating_costs"],
        ]
    ):
        total_operating_expenses = (
            inputs["rent"]
            + inputs["utilities"]
            + inputs["wages"]
            + inputs["transport"]
            + inputs["other_operating_costs"]
        )

    business_surplus_unstressed = None
    if (
        inputs["verified_revenue"] is not None
        and inputs["cogs_inventory"] is not None
        and total_operating_expenses is not None
    ):
        business_surplus_unstressed = (
            inputs["verified_revenue"]
            - inputs["cogs_inventory"]
            - total_operating_expenses
        )

    business_surplus_stressed = None
    if business_surplus_unstressed is not None and stress_factor is not None:
        business_surplus_stressed = business_surplus_unstressed * stress_factor

    total_monthly_surplus_stressed = None
    if all(
        x is not None
        for x in [
            business_surplus_stressed,
            inputs["other_monthly_income"],
            inputs["household_expenses"],
            inputs["owner_withdrawals"],
        ]
    ):
        total_monthly_surplus_stressed = (
            business_surplus_stressed
            + inputs["other_monthly_income"]
            - inputs["household_expenses"]
            - inputs["owner_withdrawals"]
        )

    total_monthly_surplus_unstressed = None
    if all(
        x is not None
        for x in [
            business_surplus_unstressed,
            inputs["other_monthly_income"],
            inputs["household_expenses"],
            inputs["owner_withdrawals"],
        ]
    ):
        total_monthly_surplus_unstressed = (
            business_surplus_unstressed
            + inputs["other_monthly_income"]
            - inputs["household_expenses"]
            - inputs["owner_withdrawals"]
        )

    stressed_dscr = safe_divide(total_monthly_surplus_stressed, monthly_installment_used)
    dscr = safe_divide(business_surplus_unstressed, monthly_installment_used)

    repayment_share = None
    if monthly_installment_used is not None and total_monthly_surplus_unstressed is not None:
        if total_monthly_surplus_unstressed <= 0:
            repayment_share = 1
        else:
            repayment_share = monthly_installment_used / total_monthly_surplus_unstressed

    income_variance = None
    if (
        inputs["stated_revenue"] is not None
        and inputs["verified_revenue"] not in [None, 0]
    ):
        income_variance = (
            abs(inputs["stated_revenue"] - inputs["verified_revenue"])
            / inputs["verified_revenue"]
        )

    equity_ratio = None
    if all(
        x is not None
        for x in [
            inputs["requested_loan_amount"],
            inputs["total_capital"],
            inputs["additional_savings_equity"],
        ]
    ) and inputs["requested_loan_amount"] != 0:
        equity_ratio = (
            inputs["total_capital"] + inputs["additional_savings_equity"]
        ) / inputs["requested_loan_amount"]

    liquidity_coverage = None
    if all(
        x is not None
        for x in [
            inputs["additional_savings_equity"],
            total_operating_expenses,
            inputs["cogs_inventory"],
            monthly_installment_used,
            inputs["owner_withdrawals"],
        ]
    ):
        denominator = (
            inputs["cogs_inventory"]
            + total_operating_expenses
            + monthly_installment_used
            + inputs["owner_withdrawals"]
        )
        liquidity_coverage = safe_divide(inputs["additional_savings_equity"], denominator)

    haircut = 0
    if inputs["collateral_type"] == "Movable":
        haircut = 0.5
    elif inputs["collateral_type"] == "Immovable":
        haircut = 0.3

    ltv = None
    if all(
        x is not None
        for x in [
            inputs["requested_loan_amount"],
            inputs["market_value"],
        ]
    ) and inputs["collateral_type"]:
        if inputs["collateral_type"] == "None":
            ltv = 99
        else:
            net_collateral = inputs["market_value"] * (1 - haircut)
            ltv = safe_divide(inputs["requested_loan_amount"], net_collateral)

    collateral_coverage = safe_divide(1, ltv)

    years_in_business = inputs["years_in_business_months"]
    age_years = inputs["age_years"]
    repeat_series = inputs["loan_series"]

    score_character = 0
    if inputs["training_certification"] == "Yes":
        score_character += 5
    if inputs["sex"] == "F":
        score_character += 3
    if years_in_business is not None:
        if years_in_business >= 36:
            score_character += 12
        elif years_in_business >= 24:
            score_character += 10
        elif years_in_business >= 12:
            score_character += 6
    if inputs["character_references"] == "Good":
        score_character += 5
    elif inputs["character_references"] == "Average":
        score_character += 2
    if age_years is not None and age_years >= 40:
        score_character += 2
    if inputs["marital_status"] == "Married":
        score_character += 1
    if inputs["repeat_borrower"] == "Yes":
        score_character += 3
    if inputs["repeat_borrower"] == "Yes" and repeat_series is not None and repeat_series >= 3:
        score_character += 5
    score_character = min(lookups["W_CHARACTER"], score_character)

    if stressed_dscr is None:
        score_capacity = 0
    elif stressed_dscr >= 1.5:
        score_capacity = 34
    elif stressed_dscr >= lookups["DSCR_TARGET"]:
        score_capacity = 28
    elif stressed_dscr >= 1.1:
        score_capacity = 18
    elif stressed_dscr >= 0.9:
        score_capacity = 8
    else:
        score_capacity = 0
    score_capacity = min(lookups["W_CAPACITY"], score_capacity)

    if equity_ratio is None:
        score_capital = 0
    elif equity_ratio >= 0.2:
        score_capital = 15
    elif equity_ratio >= 0.15:
        score_capital = 12
    elif equity_ratio >= lookups["EQUITY_MIN_RATIO"]:
        score_capital = 8
    elif equity_ratio >= 0.05:
        score_capital = 3
    else:
        score_capital = 0
    score_capital = min(lookups["W_CAPITAL"], score_capital)

    if inputs["collateral_type"] == "None":
        score_collateral = 0
    else:
        if ltv is None:
            score_collateral = 0
        elif (
            (inputs["collateral_type"] == "Movable" and ltv <= 1)
            or (inputs["collateral_type"] == "Immovable" and ltv <= 1)
        ):
            score_collateral = 10
        elif (
            (inputs["collateral_type"] == "Movable" and ltv <= lookups["LTV_MAX_MOVABLE"])
            or (
                inputs["collateral_type"] == "Immovable"
                and ltv <= lookups["LTV_MAX_IMMOVABLE"]
            )
        ):
            score_collateral = 6
        else:
            score_collateral = 0

        if inputs["collateral_insured"] == "No":
            score_collateral -= 2
    score_collateral = min(lookups["W_COLLATERAL"], score_collateral)

    if inputs["site_visit_assessment"] >= 4:
        score_conditions = 5
    elif inputs["site_visit_assessment"] == 3:
        score_conditions = 3
    else:
        score_conditions = 0
    if inputs["is_business_seasonal"] == "No":
        score_conditions += 2
    if (
        years_in_business is not None
        and inputs["stability_months"] is not None
        and inputs["stability_months"] == years_in_business
        and years_in_business >= 6
    ):
        score_conditions += 2
    sector_score = {
        "Trade": 3,
        "Service": 2,
        "Agriculture": 1,
        "Manufacturing": 1,
        "Other": 0,
    }.get(sector, 0)
    score_conditions += sector_score
    score_conditions = min(lookups["W_CONDITION"], score_conditions)

    total_score = score_character + score_capacity + score_capital + score_collateral + score_conditions
    total_score = max(1, min(99, total_score))

    flags = {
        "Age_Flag": years_in_business is None or years_in_business < lookups["BUSINESS_AGE_MIN"],
        "CFDeficit_Flag": (
            total_monthly_surplus_unstressed is not None
            and monthly_installment_used is not None
            and (
                total_monthly_surplus_unstressed <= 0
                or (
                    repayment_share is not None
                    and repayment_share > lookups["CASHFLOW_DEFICIT_REPAY_SHARE_MAX"]
                )
            )
        ),
        "Income_Var_Flag": (
            income_variance is not None and income_variance > lookups["DATA_VARIANCE_MAX"]
        ),
        "Equity_Flag": equity_ratio is not None and equity_ratio < lookups["EQUITY_MIN_RATIO"],
        "Training_Flag": inputs["training_certification"] == "No",
        "LTV_Flag": (
            ltv is not None
            and (
                (inputs["collateral_type"] == "Movable" and ltv > lookups["LTV_MAX_MOVABLE"])
                or (
                    inputs["collateral_type"] == "Immovable"
                    and ltv > lookups["LTV_MAX_IMMOVABLE"]
                )
            )
        ),
        "Collateral_Flag": (
            inputs["collateral_type"] != ""
            and inputs["collateral_insured"] != ""
            and (
                inputs["collateral_insured"] == "No"
                or inputs["collateral_type"] == "None"
            )
        ),
        "Branch_Limit_Flag": (
            inputs["requested_loan_amount"] is not None
            and inputs["requested_loan_amount"] > lookups["BRANCH_APPROVAL_LIMIT_ETB"]
        ),
        "Loan_Max_Flag": (
            inputs["requested_loan_amount"] is not None
            and inputs["requested_loan_amount"] > lookups["BUSINESS_LOAN_HARD_MAX_ETB"]
        ),
        "Default_Flag": inputs["prior_default"] == "Yes",
    }

    triggered_flags = []
    if flags["Age_Flag"]:
        triggered_flags.append("REJECT: Business less than 6 months")
    if flags["CFDeficit_Flag"]:
        triggered_flags.append("REJECT: Cash flow deficit (repayment >50% of surplus)")
    if flags["Income_Var_Flag"]:
        triggered_flags.append("REJECT: Data inconsistency (>20% variance)")
    if flags["Default_Flag"]:
        triggered_flags.append("REJECT: Prior default with HMFI")
    if flags["Loan_Max_Flag"]:
        triggered_flags.append("REJECT: Above hard max loan amount")
    if flags["Equity_Flag"]:
        triggered_flags.append("REFER: Equity <10% of loan")
    if flags["Training_Flag"]:
        triggered_flags.append("REFER: No training/certification")
    if flags["LTV_Flag"]:
        triggered_flags.append("REFER: Collateral shortfall (LTV too high)")
    if flags["Collateral_Flag"]:
        triggered_flags.append("REFER: Collateral not insured")
    if flags["Branch_Limit_Flag"]:
        triggered_flags.append("REFER: Above branch approval limit")
    if inputs["collateral_type"] == "None":
        triggered_flags.append("REJECT: No Collateral")

    if (
        flags["Age_Flag"]
        or flags["CFDeficit_Flag"]
        or flags["Income_Var_Flag"]
        or flags["Default_Flag"]
        or flags["Loan_Max_Flag"]
        or inputs["collateral_type"] == "None"
    ):
        recommendation = "REJECT"
    elif total_score <= 54:
        recommendation = "REJECT"
    elif flags["Branch_Limit_Flag"] or flags["LTV_Flag"] or flags["Collateral_Flag"]:
        recommendation = "REFER – HEAD OFFICE"
    elif total_score <= 69 or flags["Equity_Flag"] or flags["Training_Flag"]:
        recommendation = "APPROVE WITH CONDITIONS – BRANCH MANAGER"
    else:
        recommendation = "APPROVE"

    return {
        "stress_factor": stress_factor,
        "monthly_installment_used": monthly_installment_used,
        "total_operating_expenses": total_operating_expenses,
        "business_surplus_unstressed": business_surplus_unstressed,
        "business_surplus_stressed": business_surplus_stressed,
        "total_monthly_surplus_stressed": total_monthly_surplus_stressed,
        "total_monthly_surplus_unstressed": total_monthly_surplus_unstressed,
        "stressed_dscr": stressed_dscr,
        "dscr": dscr,
        "repayment_share": repayment_share,
        "income_variance": income_variance,
        "equity_ratio": equity_ratio,
        "liquidity_coverage": liquidity_coverage,
        "haircut": haircut,
        "collateral_coverage": collateral_coverage,
        "ltv": ltv,
        "score_character": score_character,
        "score_capacity": score_capacity,
        "score_capital": score_capital,
        "score_collateral": score_collateral,
        "score_conditions": score_conditions,
        "total_score": total_score,
        "risk_band": risk_band(total_score),
        "triggered_flags": triggered_flags,
        "recommendation": recommendation,
    }


def show_lookup_portal():
    st.subheader("Lookup Portal")
    st.caption("Default values are hardcoded from the workbook and can be edited here.")

    with st.form("lookup_portal_form"):
        c1, c2 = st.columns(2)
        with c1:
            dscr_target = st.number_input(
                "DSCR_TARGET",
                min_value=0.0,
                value=float(st.session_state.lookup_values["DSCR_TARGET"]),
                step=0.01,
            )
            repay_share_max = st.number_input(
                "CASHFLOW_DEFICIT_REPAY_SHARE_MAX",
                min_value=0.0,
                value=float(st.session_state.lookup_values["CASHFLOW_DEFICIT_REPAY_SHARE_MAX"]),
                step=0.01,
            )
            ltv_movable = st.number_input(
                "LTV_MAX_MOVABLE",
                min_value=0.0,
                value=float(st.session_state.lookup_values["LTV_MAX_MOVABLE"]),
                step=0.01,
            )
            ltv_immovable = st.number_input(
                "LTV_MAX_IMMOVABLE",
                min_value=0.0,
                value=float(st.session_state.lookup_values["LTV_MAX_IMMOVABLE"]),
                step=0.01,
            )
            equity_min = st.number_input(
                "EQUITY_MIN_RATIO",
                min_value=0.0,
                value=float(st.session_state.lookup_values["EQUITY_MIN_RATIO"]),
                step=0.01,
            )
            data_variance_max = st.number_input(
                "DATA_VARIANCE_MAX",
                min_value=0.0,
                value=float(st.session_state.lookup_values["DATA_VARIANCE_MAX"]),
                step=0.01,
            )
            business_age_min = st.number_input(
                "BUSINESS_AGE_MIN (months)",
                min_value=0.0,
                value=float(st.session_state.lookup_values["BUSINESS_AGE_MIN"]),
                step=1.0,
            )
        with c2:
            branch_limit = st.number_input(
                "BRANCH_APPROVAL_LIMIT_ETB",
                min_value=0.0,
                value=float(st.session_state.lookup_values["BRANCH_APPROVAL_LIMIT_ETB"]),
                step=1000.0,
            )
            hard_max = st.number_input(
                "BUSINESS_LOAN_HARD_MAX_ETB",
                min_value=0.0,
                value=float(st.session_state.lookup_values["BUSINESS_LOAN_HARD_MAX_ETB"]),
                step=10000.0,
            )
            w_character = st.number_input(
                "WEIGHT_CHARACTER",
                min_value=0.0,
                value=float(st.session_state.lookup_values["W_CHARACTER"]),
                step=1.0,
            )
            w_capacity = st.number_input(
                "WEIGHT_CAPACITY",
                min_value=0.0,
                value=float(st.session_state.lookup_values["W_CAPACITY"]),
                step=1.0,
            )
            w_capital = st.number_input(
                "WEIGHT_CAPITAL",
                min_value=0.0,
                value=float(st.session_state.lookup_values["W_CAPITAL"]),
                step=1.0,
            )
            w_collateral = st.number_input(
                "WEIGHT_COLLATERAL",
                min_value=0.0,
                value=float(st.session_state.lookup_values["W_COLLATERAL"]),
                step=1.0,
            )
            w_condition = st.number_input(
                "WEIGHT_CONDITION",
                min_value=0.0,
                value=float(st.session_state.lookup_values["W_CONDITION"]),
                step=1.0,
            )

        st.markdown("**Sector Stress Factors**")
        s1, s2, s3, s4, s5 = st.columns(5)
        sector_trade = s1.number_input(
            "Trade",
            min_value=0.0,
            value=float(st.session_state.sector_stress["Trade"]),
            step=0.01,
        )
        sector_service = s2.number_input(
            "Service",
            min_value=0.0,
            value=float(st.session_state.sector_stress["Service"]),
            step=0.01,
        )
        sector_manufacturing = s3.number_input(
            "Manufacturing",
            min_value=0.0,
            value=float(st.session_state.sector_stress["Manufacturing"]),
            step=0.01,
        )
        sector_agriculture = s4.number_input(
            "Agriculture",
            min_value=0.0,
            value=float(st.session_state.sector_stress["Agriculture"]),
            step=0.01,
        )
        sector_other = s5.number_input(
            "Other",
            min_value=0.0,
            value=float(st.session_state.sector_stress["Other"]),
            step=0.01,
        )

        save_lookup = st.form_submit_button("Save Lookup Values")
        if save_lookup:
            st.session_state.lookup_values.update(
                {
                    "DSCR_TARGET": dscr_target,
                    "CASHFLOW_DEFICIT_REPAY_SHARE_MAX": repay_share_max,
                    "LTV_MAX_MOVABLE": ltv_movable,
                    "LTV_MAX_IMMOVABLE": ltv_immovable,
                    "EQUITY_MIN_RATIO": equity_min,
                    "DATA_VARIANCE_MAX": data_variance_max,
                    "BUSINESS_AGE_MIN": business_age_min,
                    "BRANCH_APPROVAL_LIMIT_ETB": branch_limit,
                    "BUSINESS_LOAN_HARD_MAX_ETB": hard_max,
                    "W_CHARACTER": w_character,
                    "W_CAPACITY": w_capacity,
                    "W_CAPITAL": w_capital,
                    "W_COLLATERAL": w_collateral,
                    "W_CONDITION": w_condition,
                }
            )
            st.session_state.sector_stress.update(
                {
                    "Trade": sector_trade,
                    "Service": sector_service,
                    "Manufacturing": sector_manufacturing,
                    "Agriculture": sector_agriculture,
                    "Other": sector_other,
                }
            )
            st.success("Lookup values saved.")

    if st.button("Reset Lookup Values to Workbook Defaults"):
        st.session_state.lookup_values = DEFAULT_LOOKUP_VALUES.copy()
        st.session_state.sector_stress = DEFAULT_SECTOR_STRESS.copy()
        st.rerun()

    st.markdown("**Score Bands (from workbook policy)**")
    st.write(
        {
            "85-99": "Approve",
            "70-84": "Approve With Conditions",
            "55-69": "Refer Head Office",
            "1-54": "Reject",
        }
    )


def parse_number_from_state(key: str):
    value = st.session_state.get(key, "")
    if value is None:
        return None
    parsed, _ = parse_optional_float(str(value))
    return parsed


def is_non_empty(key: str) -> bool:
    value = st.session_state.get(key, "")
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def is_number_filled(key: str) -> bool:
    return parse_number_from_state(key) is not None


def step_missing_fields(step: int):
    missing = []
    if step == 1:
        checks = [
            ("credit_officer_id", "Credit Officer ID"),
            ("credit_officer_name", "Credit Officer Name"),
            ("applicant_name", "Applicant Name"),
            ("applicant_id", "Applicant ID"),
            ("sex", "Sex"),
            ("branch", "Branch"),
            ("repeat_borrower", "Repeat Borrower"),
            ("prior_default", "Prior Default"),
        ]
        for key, label in checks:
            if not is_non_empty(key):
                missing.append(label)
        num_checks = [
            ("age_years", "Age (years)"),
            ("requested_loan_amount", "Requested Loan Amount"),
        ]
        for key, label in num_checks:
            if not is_number_filled(key):
                missing.append(label)
        has_installment_override = is_number_filled("monthly_installment_override")
        has_term = is_number_filled("term_months")
        has_rate = is_number_filled("annual_interest_rate")
        if not has_installment_override and not (has_term and has_rate):
            missing.append(
                "Monthly Installment override OR both Term (months) and Annual Interest Rate"
            )
    elif step == 2:
        checks = [
            ("business_name", "Business Name"),
            ("sector", "Sector"),
            ("training_certification", "Training/Certification"),
            ("is_business_seasonal", "Is Business Seasonal"),
            ("character_references", "Character References"),
        ]
        for key, label in checks:
            if not is_non_empty(key):
                missing.append(label)
        num_checks = [
            ("years_in_business_months", "Years in Business"),
            ("stability_months", "Stability of Business Location"),
        ]
        for key, label in num_checks:
            if not is_number_filled(key):
                missing.append(label)
    elif step == 3:
        num_checks = [
            ("stated_revenue", "Stated Revenue"),
            ("verified_revenue", "Verified Revenue"),
            ("cogs_inventory", "COGS / Inventory"),
            ("rent", "Rent"),
            ("utilities", "Utilities"),
            ("wages", "Wages"),
            ("transport", "Transport"),
            ("other_operating_costs", "Other Operating Costs"),
            ("other_monthly_income", "Other Monthly Income"),
            ("household_expenses", "Household Expenses"),
            ("owner_withdrawals", "Owner Withdrawals"),
        ]
        for key, label in num_checks:
            if not is_number_filled(key):
                missing.append(label)
    elif step == 4:
        num_checks = [
            ("total_capital", "Total Capital"),
            ("additional_savings_equity", "Cash at Bank / Additional Savings / Equity"),
        ]
        for key, label in num_checks:
            if not is_number_filled(key):
                missing.append(label)
    elif step == 5:
        if not is_non_empty("collateral_type"):
            missing.append("Collateral Type")
        if not is_non_empty("collateral_insured"):
            missing.append("Collateral Insured")
        if st.session_state.get("collateral_type") in ["Movable", "Immovable"] and not is_number_filled(
            "market_value"
        ):
            missing.append("Market Value")
    return missing


def build_inputs_from_state():
    loan_series_raw = st.session_state.get("loan_series", "")
    loan_series = None
    if loan_series_raw:
        loan_series = 5.0 if loan_series_raw == "5+" else float(loan_series_raw)

    return {
        "credit_officer_id": st.session_state.get("credit_officer_id", ""),
        "credit_officer_name": st.session_state.get("credit_officer_name", ""),
        "applicant_name": st.session_state.get("applicant_name", ""),
        "applicant_id": st.session_state.get("applicant_id", ""),
        "sex": st.session_state.get("sex", ""),
        "age_years": parse_number_from_state("age_years"),
        "marital_status": st.session_state.get("marital_status", ""),
        "literacy": st.session_state.get("literacy", ""),
        "repeat_borrower": st.session_state.get("repeat_borrower", ""),
        "loan_series": loan_series,
        "prior_default": st.session_state.get("prior_default", ""),
        "branch": st.session_state.get("branch", ""),
        "application_date": st.session_state.get("application_date", date.today()),
        "requested_loan_amount": parse_number_from_state("requested_loan_amount"),
        "monthly_installment_override": parse_number_from_state("monthly_installment_override"),
        "term_months": parse_number_from_state("term_months"),
        "annual_interest_rate": parse_number_from_state("annual_interest_rate"),
        "business_name": st.session_state.get("business_name", ""),
        "ownership": st.session_state.get("ownership", ""),
        "site_visit_assessment": int(st.session_state.get("site_visit_assessment", 0)),
        "sector": st.session_state.get("sector", ""),
        "training_certification": st.session_state.get("training_certification", ""),
        "is_business_seasonal": st.session_state.get("is_business_seasonal", ""),
        "business_type": st.session_state.get("business_type", ""),
        "years_in_business_months": parse_number_from_state("years_in_business_months"),
        "character_references": st.session_state.get("character_references", ""),
        "loan_purpose": st.session_state.get("loan_purpose", ""),
        "stability_months": parse_number_from_state("stability_months"),
        "stated_revenue": parse_number_from_state("stated_revenue"),
        "verified_revenue": parse_number_from_state("verified_revenue"),
        "cogs_inventory": parse_number_from_state("cogs_inventory"),
        "other_monthly_income": parse_number_from_state("other_monthly_income"),
        "rent": parse_number_from_state("rent"),
        "household_expenses": parse_number_from_state("household_expenses"),
        "utilities": parse_number_from_state("utilities"),
        "owner_withdrawals": parse_number_from_state("owner_withdrawals"),
        "wages": parse_number_from_state("wages"),
        "transport": parse_number_from_state("transport"),
        "other_operating_costs": parse_number_from_state("other_operating_costs"),
        "total_capital": parse_number_from_state("total_capital"),
        "additional_savings_equity": parse_number_from_state("additional_savings_equity"),
        "collateral_type": st.session_state.get("collateral_type", ""),
        "collateral_insured": st.session_state.get("collateral_insured", ""),
        "market_value": parse_number_from_state("market_value"),
    }


def show_scorecard_results():
    if "last_result" not in st.session_state:
        return

    result = st.session_state.last_result
    st.markdown("## 6) Outputs (Score, Flags, Decision)")
    o1, o2, o3 = st.columns(3)
    o1.metric("Total Score (1-99)", f"{result['total_score']:.2f}")
    o2.metric("Risk Band", result["risk_band"])
    o3.metric("Decision Recommendation", result["recommendation"])

    st.markdown("**Category Scores**")
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Character", f"{result['score_character']:.2f}")
    s2.metric("Capacity", f"{result['score_capacity']:.2f}")
    s3.metric("Capital", f"{result['score_capital']:.2f}")
    s4.metric("Collateral", f"{result['score_collateral']:.2f}")
    s5.metric("Conditions", f"{result['score_conditions']:.2f}")

    st.markdown("**Derived Metrics**")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Monthly Installment (Used)", format_number(result["monthly_installment_used"]))
    d2.metric("Stressed DSCR", format_number(result["stressed_dscr"]))
    d3.metric("Repayment Share", format_number(result["repayment_share"]))
    d4.metric("Income Variance", format_number(result["income_variance"]))
    d5, d6, d7, d8 = st.columns(4)
    d5.metric("Equity Ratio", format_number(result["equity_ratio"]))
    d6.metric("LTV", format_number(result["ltv"]))
    d7.metric("Collateral Coverage", format_number(result["collateral_coverage"]))
    d8.metric("Stress Factor (Sector)", format_number(result["stress_factor"]))

    st.markdown("**Triggered Flags**")
    if result["triggered_flags"]:
        for flag in result["triggered_flags"]:
            st.write(f"- {flag}")
    else:
        st.write("- No flags triggered")


def show_scorecard():
    st.subheader("Business Loan Scorecard")
    st.caption("Wizard mode: complete each step and continue.")

    if "scorecard_step" not in st.session_state:
        st.session_state.scorecard_step = 1

    top_left, top_right = st.columns([0.7, 0.3])
    with top_right:
        if st.button("Reset Form Defaults"):
            reset_customer_defaults()
            if "last_result" in st.session_state:
                del st.session_state["last_result"]
            st.rerun()

    steps = {
        1: "Applicant & Loan Request",
        2: "Business Details",
        3: "Affordability / Cash Flow",
        4: "Equity / Capital",
        5: "Collateral",
        6: "Review & Output",
    }
    current_step = st.session_state.scorecard_step
    st.progress(current_step / 6)
    st.markdown(f"**Step {current_step} of 6: {steps[current_step]}**")

    if current_step == 1:
        a1, a2, a3 = st.columns(3)
        with a1:
            st.text_input("Credit Officer ID", key="credit_officer_id")
            st.text_input("Applicant Name", key="applicant_name")
            optional_number("Age (years)", "age_years")
            st.selectbox("Repeat Borrower?", ["", "Yes", "No"], key="repeat_borrower")
            st.selectbox(
                "Branch",
                ["", "Head Office", "Hakim", "Sofi", "Erer", "Other"],
                key="branch",
            )
            optional_number("Requested Loan Amount (ETB)", "requested_loan_amount")
            optional_number("Term (months)", "term_months")
        with a2:
            st.text_input("Credit Officer Name", key="credit_officer_name")
            st.text_input("Applicant ID", key="applicant_id")
            st.selectbox(
                "Marital Status",
                ["", "Married", "Single", "Widowed"],
                key="marital_status",
            )
            st.selectbox("Loan Series", ["", "2", "3", "4", "5+"], key="loan_series")
            st.date_input("Application Date", key="application_date")
            optional_number("Monthly Installment (if extra payments)", "monthly_installment_override")
            optional_number("Annual Interest Rate (%)", "annual_interest_rate")
        with a3:
            st.selectbox("Sex (M/F)", ["", "M", "F"], key="sex")
            st.selectbox(
                "Primary Applicant Literacy Level",
                [
                    "",
                    "No Formal Education",
                    "Elementary/Primary",
                    "Secondary/High School",
                    "University",
                    "College/TVET",
                ],
                key="literacy",
            )
            st.selectbox(
                "Prior Default with HMFI or other institutions?",
                ["", "Yes", "No"],
                key="prior_default",
            )

    elif current_step == 2:
        b1, b2, b3 = st.columns(3)
        with b1:
            st.text_input("Business Name", key="business_name")
            st.selectbox(
                "Sector",
                ["", "Trade", "Service", "Manufacturing", "Agriculture", "Other"],
                key="sector",
            )
            st.text_input("Business Type / Description", key="business_type")
            st.selectbox(
                "Loan Purpose",
                [
                    "",
                    "Working Capital",
                    "Inventory Financing",
                    "Equipment Purchase",
                    "Business Expansion",
                    "Agricultural Input (seeds, fertilizer, feed etc)",
                    "Livestock Purchse",
                    "Other",
                ],
                key="loan_purpose",
            )
        with b2:
            st.selectbox(
                "Ownership Structure",
                ["", "Sole Proprietor", "Partnership", "PLC", "Share Company", "Informal", "Other"],
                key="ownership",
            )
            st.selectbox(
                "Training/Certification?",
                ["", "Yes", "No"],
                key="training_certification",
            )
            optional_number("Years in Business (months)", "years_in_business_months")
            optional_number("Stability of Business Location (months)", "stability_months")
        with b3:
            st.selectbox(
                "Site Visit Assessment (0-5)",
                [0, 1, 2, 3, 4, 5],
                key="site_visit_assessment",
            )
            st.selectbox(
                "Is Business Seasonal?",
                ["", "Yes", "No"],
                key="is_business_seasonal",
            )
            st.selectbox(
                "Character References",
                ["", "Good", "Average", "Poor"],
                key="character_references",
            )

    elif current_step == 3:
        c1, c2 = st.columns(2)
        with c1:
            optional_number("Stated Average Monthly Revenue (ETB)", "stated_revenue")
            optional_number("COGS / Inventory", "cogs_inventory")
            optional_number("Rent", "rent")
            optional_number("Utilities", "utilities")
            optional_number("Wages", "wages")
            optional_number("Transport", "transport")
            optional_number("Other Operating Costs (incl. taxes)", "other_operating_costs")
        with c2:
            optional_number("Bank Statement Verified Avg Monthly Revenue (ETB)", "verified_revenue")
            optional_number("Other Monthly Income", "other_monthly_income")
            optional_number("Household Expenses", "household_expenses")
            optional_number("Owner Withdrawals/Dividend Monthly Average", "owner_withdrawals")

    elif current_step == 4:
        d1, d2 = st.columns(2)
        with d1:
            optional_number("Total Capital", "total_capital")
        with d2:
            optional_number("Cash at Bank / Additional Savings / Equity (ETB)", "additional_savings_equity")

    elif current_step == 5:
        e1, e2 = st.columns(2)
        with e1:
            st.selectbox(
                "Collateral Type",
                ["", "Movable", "Immovable", "None"],
                key="collateral_type",
            )
            optional_number("Market Value (ETB)", "market_value")
        with e2:
            st.selectbox(
                "Collateral Insured?",
                ["", "Yes", "No"],
                key="collateral_insured",
            )

    else:
        st.info("Review complete. Click Calculate Scorecard to generate outputs.")
        if st.button("Calculate Scorecard", type="primary"):
            inputs = build_inputs_from_state()
            st.session_state.last_result = calculate_scorecard(
                inputs,
                st.session_state.lookup_values,
                st.session_state.sector_stress,
            )
        show_scorecard_results()

    nav_left, nav_right = st.columns(2)
    if current_step > 1:
        if nav_left.button("Previous"):
            st.session_state.scorecard_step -= 1
            st.rerun()

    if current_step < 6:
        next_label = "Review & Output" if current_step == 5 else "Save and Continue"
        if nav_right.button(next_label, type="primary"):
            missing = step_missing_fields(current_step)
            if missing:
                st.warning(f"Please complete: {', '.join(missing[:6])}" + ("..." if len(missing) > 6 else ""))
            else:
                st.session_state.scorecard_step += 1
                st.rerun()


def show_model_notes():
    st.subheader("Model Notes")
    st.write("Use BL scorecard inputs and complete required fields.")
    st.write("Outputs include stressed DSCR, category scores, total score (1-99), flags, and recommendation.")
    st.write("Hard stops: repayment >50% of surplus, income variance >20%, business age <6 months.")
    st.write("Refer flags: equity <10%, no training, collateral shortfall/uninsured, above branch limit.")
    st.write("Score bands: 85-99 approve, 70-84 approve with conditions, 55-69 refer head office, 1-54 reject.")
    st.write("Policy values can be edited in the Lookup Portal tab.")


def main():
    st.set_page_config(page_title="HMFI BL Scorecard", layout="wide")
    init_state()

    st.title("HMFI Business Loan Scorecard v1")
    st.caption("Streamlit implementation of HMFI_BL_Scorecard_v1.xlsx")

    tab_scorecard, tab_lookup, tab_notes = st.tabs(
        ["Scorecard", "Lookup Portal", "Readme"]
    )

    with tab_scorecard:
        show_scorecard()
    with tab_lookup:
        show_lookup_portal()
    with tab_notes:
        show_model_notes()


if __name__ == "__main__":
    main()
