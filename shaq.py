from collections import defaultdict
from pathlib import Path
import sqlite3

import streamlit as st
import altair as alt
import pandas as pd

import math
import scipy.stats as stat
from statistics import NormalDist
from streamlit_option_menu import option_menu

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='Inventory tracker',
    page_icon=':gear:', # This is an emoji shortcode. Could be a URL too.
)

# Sidebar Nav
with st.sidebar:
    selected = option_menu(
        menu_title="Menu",
        options=["Inventory Database","Optimization Calculator","Manual"],
        icons = ["box", "calculator", "book"],
        menu_icon=["Menu"],
        default_index=0,
    )

if selected == 'Inventory Database':

    # Set the title and favicon that appear in the Browser's tab bar.
    # st.title('Inventory Database')

    # -----------------------------------------------------------------------------
    # Declare some useful functions.

    def connect_db():
        '''Connects to the sqlite database.'''

        DB_FILENAME = Path(__file__).parent/'inventory2.db'
        db_already_exists = DB_FILENAME.exists()

        conn = sqlite3.connect(DB_FILENAME, check_same_thread=False)
        db_was_just_created = not db_already_exists

        return conn, db_was_just_created


    def initialize_data(conn):
        '''Initializes the inventory table with some data.'''
        cursor = conn.cursor()

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_number TEXT,
                component TEXT,
                quantity REAL,
                annual_demand REAL,
                std_deviation REAL,
                lead_time REAL,
                unit_cost REAL,
                ordering_cost REAL,
                storage_cost REAL,
                shortage_cost REAL,
                ordering_quantity REAL,
                reorder_level REAL,
                service_level REAL,
                total_cost REAL
            )
            '''
        )

        cursor.execute(
            '''
            INSERT INTO inventory
                (part_number, component, quantity, annual_demand, std_deviation, lead_time, unit_cost, ordering_cost, storage_cost, shortage_cost, ordering_quantity, reorder_level,
                service_level, total_cost)
            VALUES
                -- Beverages
                ('AXXXX', 'A', 600, 281, 18, 3, 65781, 6500000, 130000, 180000, 542, 80, 97.15, 25733842),
                ('BXXXX', 'B', 600, 281, 18, 3, 65781, 6500000, 130000, 180000, 542, 80, 97.15, 25733842),
                ('CXXXX', 'C', 600, 281, 18, 3, 65781, 6500000, 130000, 180000, 542, 80, 97.15, 25733842),
                ('DXXXX', 'D', 600, 281, 18, 3, 65781, 6500000, 130000, 180000, 542, 80, 97.15, 25733842),
                ('EXXXX', 'E', 600, 281, 18, 3, 65781, 6500000, 130000, 180000, 542, 80, 97.15, 25733842),
                ('FXXXX', 'F', 600, 281, 18, 3, 65781, 6500000, 130000, 180000, 542, 80, 97.15, 25733842),
                ('GXXXX', 'G', 600, 281, 18, 3, 65781, 6500000, 130000, 180000, 542, 80, 97.15, 25733842),
                ('HXXXX', 'H', 600, 281, 18, 3, 65781, 6500000, 130000, 180000, 542, 80, 97.15, 25733842),
                ('IXXXX', 'I', 600, 281, 18, 3, 65781, 6500000, 130000, 180000, 542, 80, 97.15, 25733842),
                ('JXXXX', 'J', 600, 281, 18, 3, 65781, 6500000, 130000, 180000, 542, 80, 97.15, 25733842)

            '''
        )
        conn.commit()


    def load_data(conn):
        '''Loads the inventory data from the database.'''
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT * FROM inventory')
            data = cursor.fetchall()
        except:
            return None

        df = pd.DataFrame(data,
            columns=[
                'id',
                'part_number',
                'component',
                'quantity',
                'annual_demand',
                'std_deviation',
                'lead_time',
                'unit_cost',
                'ordering_cost',
                'storage_cost',
                'shortage_cost',
                'ordering_quantity',
                'reorder_level',
                'service_level',
                'total_cost'
            ])

        return df


    def update_data(conn, df, changes):
        '''Updates the inventory data in the database.'''
        cursor = conn.cursor()

        if changes['edited_rows']:
            deltas = st.session_state.inventory_table['edited_rows']
            rows = []

            for i, delta in deltas.items():
                row_dict = df.iloc[i].to_dict()
                row_dict.update(delta)
                rows.append(row_dict)

            cursor.executemany(
                '''
                UPDATE inventory
                SET
                    part_number = :part_number,
                    component = :component,
                    quantity = :quantity,
                    annual_demand = :annual_demand,
                    std_deviation = :std_deviation,
                    lead_time = :lead_time,
                    unit_cost = :unit_cost,
                    ordering_cost = :ordering_cost,
                    storage_cost = :storage_cost,
                    shortage_cost = :shortage_cost,
                    ordering_quantity = :ordering_quantity,
                    reorder_level = :reorder_level,
                    service_level = :service_level,
                    total_cost = :total_cost

                WHERE id = :id
                ''',
                rows,
            )

        if changes['added_rows']:
            cursor.executemany(
                '''
                INSERT INTO inventory
                    (id, part_number, component, quantity, annual_demand, std_deviation, lead_time, unit_cost, ordering_cost, storage_cost, shortage_cost, ordering_quantity, reorder_level, service_level, total_cost)
                VALUES
                    (:id, :part_number, :component, :quantity, :annual_demand, :std_deviation, :lead_time, :unit_cost, :ordering_cost, :storage_cost, :shortage_cost, :ordering_quantity, :reorder_level, :service_level, :total_cost)
                ''',
                (defaultdict(lambda: None, row) for row in changes['added_rows']),
            )

        if changes['deleted_rows']:
            cursor.executemany(
                'DELETE FROM inventory WHERE id = :id',
                ({'id': int(df.loc[i, 'id'])} for i in changes['deleted_rows'])
            )

        conn.commit()


    # -----------------------------------------------------------------------------
    # Draw the actual page, starting with the inventory table.

    # Set the title that appears at the top of the page.
    '''
    # :gear: Inventory tracker

    **Welcome to Alice's Corner Store's intentory tracker!**
    This page reads and writes directly from/to our inventory database.
    '''

    st.info('''
        Use the table below to add, remove, and edit items.
        And don't forget to commit your changes when you're done.
        ''')

    # Connect to database and create table if needed
    conn, db_was_just_created = connect_db()

    # Initialize data.
    if db_was_just_created:
        initialize_data(conn)
        st.toast('Database initialized with some sample data.')

    # Load data from database
    df = load_data(conn)

    # Display data with editable table
    edited_df = st.data_editor(
        df,
        disabled=['id'], # Don't allow editing the 'id' column.
        num_rows='dynamic', # Allow appending/deleting rows.
        column_config={
            # Show dollar sign before price columns.
            "unit_cost": st.column_config.NumberColumn(format="$%.2f"),
            "ordering_cost": st.column_config.NumberColumn(format="$%.2f"),
        },
        key='inventory_table')

    has_uncommitted_changes = any(len(v) for v in st.session_state.inventory_table.values())

    st.button(
        'Commit changes',
        type='primary',
        disabled=not has_uncommitted_changes,
        # Update data in database
        on_click=update_data,
        args=(conn, df, st.session_state.inventory_table))


    # -----------------------------------------------------------------------------
    # Now some cool charts

    # Add some space
    ''
    ''
    ''

    st.subheader('Units left', divider='red')

    need_to_reorder = df[df['quantity'] < df['reorder_level']].loc[:, 'component']

    if len(need_to_reorder) > 0:
        items = '\n'.join(f'* {name}' for name in need_to_reorder)

        st.error(f"We're running dangerously low on the items below:\n {items}")

    ''
    ''

    st.altair_chart(
        # Layer 1: Bar chart.
        alt.Chart(df)
            .mark_bar(
                orient='horizontal',
            )
            .encode(
                x='quantity',
                y='component',
            )
        # Layer 2: Chart showing the reorder point.
        + alt.Chart(df)
            .mark_point(
                shape='diamond',
                filled=True,
                size=50,
                color='salmon',
                opacity=1,
            )
            .encode(
                x='reorder_level',
                y='component',
            )
        ,
        use_container_width=True)

    st.caption('NOTE: The :diamonds: location shows the reorder point.')

    ''
    ''
    ''

    # -----------------------------------------------------------------------------

    st.subheader('Best sellers', divider='orange')

    ''
    ''

    st.altair_chart(alt.Chart(df)
        .mark_bar(orient='horizontal')
        .encode(
            x='quantity',
            y=alt.Y('component',sort='-x'),
        ),
        use_container_width=True)

if selected == 'Optimization Calculator':
    st.title("Optimization Calculator")
    
    # user inputs on sidebar
    D = st.number_input("Annual Demand: ", min_value = 10)
    std = st.number_input("Standard Deviation: ", min_value = 10)
    # L = st.sidebar.number_input("Lead Time: ", min_value = 10)
    L = st.slider("Lead Time: ", min_value = 1, max_value = 30)
    p = st.number_input("Unit Cost: ", min_value = 10)
    A = st.number_input("Ordering Cost: ", min_value = 10)
    # h = int(input("Storing Cost: "))
    h = 0.2*p
    Cu = st.number_input("Shortage Cost", min_value = 10)

    D_L = D*L/12 
    std_L = std*math.sqrt(L/12)

    # Solve

    q_global = math.sqrt(2*A*D/h)
    alpha_init = h*q_global/Cu/D
    print(alpha_init)
    z = stat.norm.ppf(1-alpha_init)
    print("z: ", z)

    r_initial = D_L + z*std_L
    print(r_initial)

    V = True

    while V :
        
        # Finding Q
        
        # Calculate N
        pdf = math.exp(-0.5*z*z)/(math.sqrt(2*math.pi))
        # print(pdf)
        pos = pdf - z*(1-NormalDist().cdf(z))
        #print(pos)
        N = math.ceil(std_L*(pdf-z*pos))
        print("N: ", N)

        q = math.sqrt(2*D*(A+Cu*N)/h)                                                                                                                                                             
    #print(q)
        alpha = h*q/Cu/D
        z = stat.norm.ppf(1-alpha)
        r_2 = D_L + z*std_L
        #print(r_2)
        if abs(r_2 - r_initial) > 0.01:
            r_initial = r_2
            V = True
            
        else:
            V = False

    # Service Level and Total Cost

    # Service Level

    ss_unrounded =  (1 - (N / D_L))  * 100 
    print("srvc level: ", ss_unrounded)
    sl = round(ss_unrounded,2)
    print("Service Level: ", sl)


    # Total Cost

    OT_unrounded = D * p + (A*D/q) + (h*(0.5*q + r_2 - D_L)) + (Cu*(D/q)*N)
    print("OT: ", OT_unrounded)
    OT = round(OT_unrounded,2)
    print("Total Cost: ", OT)

    # Main Body

    st.header("*Optimized Result using Q model (continuous review)*")

    #Outputs
    st.write(f"Optimum Reorder Level :")
    st.info(round(r_2))

    st.write(f"Optimum Ordering Quantity :")
    st.info(round(q))

    st.write(f"Service Level (%) :")
    st.info(sl)

    st.write(f"Optimized Total Cost :")
    st.info(OT)

