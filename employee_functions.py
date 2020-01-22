import os
import json
import math
import numpy as np
import game_parameters.constants as c
import table_operations as to


with open(os.path.join(c.PARAMS_FOLDER, 'person_names.json'), 'r') as f:
    PERSON_NAMES = json.load(f)
PERSON_NAMES['male'] += PERSON_NAMES['unisex']
PERSON_NAMES['female'] += PERSON_NAMES['unisex']


UNEMPLOYED = 1  # employer_id to indicate unemployed


def generate_employee(employee_type='random', points='random', employer=UNEMPLOYED):
    """
    Generate a new employee and add them to the database.
    Args:
        employee_type (str): Type of employee to generate. If 'random' will select one
            from the employees.json file.
        points (int or 'random'): How many skill points to assign per skill. If 'random'
            will give a normally distributed number.
        employer (int): Owner_id of the employer.
    Returns:
        Int. The employee_id of the new employee.
    """

    if employee_type == 'random':
        employee_type = np.random.choice(list(c.EMPLOYEES.keys()), 1)[0]

    params = {'employee_type': employee_type}

    # Provide some skills to the employee
    skills = c.EMPLOYEES[employee_type]['bonuses']
    if points == 'random':
        points = int(round(np.random.normal(c.MEAN_POINTS, c.STD_POINTS, 1)[0]))
    points *= len(skills)

    assignments = np.random.choice(range(len(skills)), points)
    for i, s in enumerate(skills.keys()):
        levels = skills[s]['levels']
        params[s] = levels[min(np.sum(assignments == i), len(levels) - 1)]

    # Determine salary
    params['salary'] = points*c.SALARY_MULTIPLIER + c.BASE_SALARY

    # Generate a name
    if np.random.choice(['m', 'f'], 1)[0] == 'm':
        name = np.random.choice(PERSON_NAMES['male'], 1)[0]
    else:
        name = np.random.choice(PERSON_NAMES['female'], 1)[0]
    name = name + ' ' + np.random.choice(PERSON_NAMES['last'], 1)[0]
    params['name'] = name

    # Assign employer
    params['employer'] = employer

    # Add to the database
    new_id = to.insert_into_table('employees', params)
    return new_id


def hire_employee(employee_id, hirer_id):
    """
    Hire an employee who is currently unemployed.

    Args:
        employee_id (int): ID of the employee to hire.
        hirer_id (int): ID of the owner who is hiring the employee.

    Returns:
        None.
    """
    query = "SELECT employee_id, employer FROM employees WHERE employee_id = ?"
    data = to.query_to_dataframe(query, [employee_id])
    if len(data) == 0:
        raise ValueError(f"Employee {employee_id} doesn't exist.")
    data = data.iloc[0]
    if data['employer'] != UNEMPLOYED:
        raise ValueError(f"Employee {employee_id} is not unemployed and so cannot be hired.")
    command = "UPDATE employees SET employer = ? WHERE employee_id = ?"
    to.cursor.execute(command, [hirer_id, employee_id])


def fire_employee(employee_id):
    """
    Return an employee to unemployed status.
    Args:
        employee_id (int): ID of the employee to fire.

    Returns:
        None.
    """
    query = "SELECT employee_id FROM employees WHERE employee_id = ?"
    data = to.query_to_dataframe(query, [employee_id])
    if len(data) == 0:
        raise ValueError(f"Employee {employee_id} doesn't exist.")
    command = "UPDATE employees SET employer = ? WHERE employee_id = ?"
    to.cursor.execute(command, [UNEMPLOYED, employee_id])


def total_salary(employer_id):
    """
    Return the total salary that an employer is paying.
    Args:
        employer_id (int): ID of the employer (owner).

    Returns:
        Float. How much salary they owe.
    """
    data = to.query_to_dataframe(
        "SELECT salary FROM employees WHERE employer = ?", [employer_id])
    if len(data) == 0:
        return 0
    return sum(data['salary'])


def employee_bonus(employer_id, bonus_name):
    """
    Return the bonus that the employees of an employer generate.
    Args:
        employer_id (int): Employer (owner) in question.
        bonus_name (str): Name of the bonus.

    Returns:
        Float. Bonus that the employees generate.
    """
    horses = to.query_to_dataframe(
        "SELECT horse_id FROM horses WHERE owner_id = ? AND death_date IS NULL", [employer_id])

    bonus = 0
    for emp, e_info in c.EMPLOYEES.items():

        try:
            bonus_info = e_info['bonuses'][bonus_name]
        except KeyError:
            continue
        employees = to.query_to_dataframe(
            f"SELECT {bonus_name} FROM employees WHERE employer = ? AND employee_type = ?",
            [employer_id, emp])
        employees.sort_values(by=bonus_name, ascending=False, inplace=True)

        # How many of this type of employee can have their bonus count
        used_employees = min(len(employees), math.ceil(len(horses) / bonus_info['horses_per']))
        if used_employees == 0:
            continue

        total_red = employees.iloc[:used_employees][bonus_name].sum() * bonus_info[
            'horses_per']
        bonus += total_red / max(used_employees * bonus_info['horses_per'], len(horses))
    return bonus
