import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
import random
from datetime import datetime, timedelta
import json

# Page configuration
st.set_page_config(
    page_title="Cell Management System",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .cell-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        color: white;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        backdrop-filter: blur(4px);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    .cell-card-charging {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
    .cell-card-discharging {
        background: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%);
    }
    .cell-card-idle {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    .cell-title {
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 1rem;
        text-align: center;
    }
    .cell-metric {
        display: flex;
        justify-content: space-between;
        margin: 0.3rem 0;
        font-size: 0.9rem;
    }
    .cell-metric-value {
        font-weight: bold;
    }
    .task-info {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    .status-charging {
        color: #28a745;
        font-weight: bold;
    }
    .status-discharging {
        color: #dc3545;
        font-weight: bold;
    }
    .status-idle {
        color: #ffc107;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'cells_data' not in st.session_state:
    st.session_state.cells_data = {}
if 'tasks_data' not in st.session_state:
    st.session_state.tasks_data = {}
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False
if 'historical_data' not in st.session_state:
    st.session_state.historical_data = []
if 'current_task_index' not in st.session_state:
    st.session_state.current_task_index = 0

def create_cell_data(cell_type, cell_id):
    """Create cell data based on type"""
    voltage = 3.2 if cell_type == "lfp" else 3.6
    min_voltage = 2.8 if cell_type == "lfp" else 3.2
    max_voltage = 3.6 if cell_type == "lfp" else 4.0
    current = 0.0
    temp = round(random.uniform(25, 40), 1)
    capacity = round(voltage * current, 2)
    
    return {
        "voltage": voltage,
        "current": current,
        "temp": temp,
        "capacity": capacity,
        "min_voltage": min_voltage,
        "max_voltage": max_voltage,
        "soc": random.randint(20, 90),  # State of Charge
        "health": random.randint(85, 100),  # Battery Health
        "status": "IDLE"
    }

def simulate_battery_operation(cell_data, task_type, task_params):
    """Simulate battery operation based on task"""
    if task_type == "CC_CV":
        # Charging simulation
        cell_data["current"] = task_params.get("current", 1.0)
        cell_data["voltage"] = min(cell_data["voltage"] + 0.01, cell_data["max_voltage"])
        cell_data["soc"] = min(cell_data["soc"] + 0.5, 100)
        cell_data["status"] = "CHARGING"
        
    elif task_type == "CC_CD":
        # Discharging simulation
        cell_data["current"] = -abs(task_params.get("current", 1.0))
        cell_data["voltage"] = max(cell_data["voltage"] - 0.01, cell_data["min_voltage"])
        cell_data["soc"] = max(cell_data["soc"] - 0.3, 0)
        cell_data["status"] = "DISCHARGING"
        
    else:  # IDLE
        cell_data["current"] = 0.0
        cell_data["status"] = "IDLE"
    
    # Update temperature based on current
    if abs(cell_data["current"]) > 0:
        cell_data["temp"] += random.uniform(-0.5, 0.5)
        cell_data["temp"] = max(20, min(50, cell_data["temp"]))
    
    # Update capacity
    cell_data["capacity"] = round(cell_data["voltage"] * abs(cell_data["current"]), 2)
    
    return cell_data

# Main title
st.markdown('<h1 class="main-header">🔋 Cell Management System</h1>', unsafe_allow_html=True)

# Sidebar for configuration
st.sidebar.header("⚙️ Configuration")

# Cell Configuration
st.sidebar.subheader("Cell Configuration")
num_cells = st.sidebar.number_input("Number of Cells", min_value=1, max_value=10, value=2)

# Initialize or update cells
for i in range(num_cells):
    cell_key = f"cell_{i+1}"
    if cell_key not in st.session_state.cells_data:
        cell_type = st.sidebar.selectbox(f"Cell {i+1} Type", ["lfp", "nmc"], key=f"type_{i}")
        st.session_state.cells_data[cell_key] = create_cell_data(cell_type, i+1)
        st.session_state.cells_data[cell_key]["type"] = cell_type

# Task Configuration
st.sidebar.subheader("Task Sequence Configuration")

# Initialize task sequence in session state
if 'task_sequence' not in st.session_state:
    st.session_state.task_sequence = []
if 'current_task_step' not in st.session_state:
    st.session_state.current_task_step = 0
if 'task_start_time' not in st.session_state:
    st.session_state.task_start_time = None

# Add new task to sequence
st.sidebar.write("**Add Task to Sequence:**")
new_task_type = st.sidebar.selectbox("Select Task Type", ["CC_CV", "CC_CD", "IDLE"], key="new_task")

new_task_params = {}
if new_task_type == "CC_CV":
    st.sidebar.write("Charging Parameters:")
    new_task_params["current"] = st.sidebar.slider("Current (A)", 0.1, 5.0, 1.0, key="cc_cv_current")
    new_task_params["cv_voltage"] = st.sidebar.slider("CV Voltage (V)", 3.0, 4.2, 4.0, key="cc_cv_voltage")
    new_task_params["time_seconds"] = st.sidebar.slider("Time (seconds)", 10, 300, 60, key="cc_cv_time")
    
elif new_task_type == "CC_CD":
    st.sidebar.write("Discharging Parameters:")
    new_task_params["current"] = st.sidebar.slider("Current (A)", 0.1, 5.0, 1.0, key="cc_cd_current")
    new_task_params["voltage"] = st.sidebar.slider("Cut-off Voltage (V)", 2.5, 3.5, 3.0, key="cc_cd_voltage")
    new_task_params["time_seconds"] = st.sidebar.slider("Time (seconds)", 10, 300, 60, key="cc_cd_time")
    
else:  # IDLE
    new_task_params["time_seconds"] = st.sidebar.slider("Idle Time (seconds)", 5, 120, 30, key="idle_time")

# Add task button
if st.sidebar.button("➕ Add Task to Sequence"):
    task_info = {
        "type": new_task_type,
        "params": new_task_params.copy(),
        "completed": False
    }
    st.session_state.task_sequence.append(task_info)
    st.sidebar.success(f"Added {new_task_type} to sequence!")

# Display current task sequence
st.sidebar.write("**Current Task Sequence:**")
if st.session_state.task_sequence:
    for idx, task in enumerate(st.session_state.task_sequence):
        status_icon = "✅" if task["completed"] else ("🔄" if idx == st.session_state.current_task_step else "⏳")
        st.sidebar.write(f"{status_icon} {idx+1}. {task['type']} ({task['params'].get('time_seconds', 0)}s)")
else:
    st.sidebar.info("No tasks in sequence. Add tasks above.")

# Clear sequence button
if st.sidebar.button("🗑️ Clear Sequence"):
    st.session_state.task_sequence = []
    st.session_state.current_task_step = 0
    st.session_state.task_start_time = None

# Get current task parameters
if st.session_state.task_sequence and st.session_state.current_task_step < len(st.session_state.task_sequence):
    current_task = st.session_state.task_sequence[st.session_state.current_task_step]
    task_type = current_task["type"]
    task_params = current_task["params"]
else:
    task_type = "IDLE"
    task_params = {"time_seconds": 30}

# Control buttons
col1, col2, col3 = st.sidebar.columns(3)
start_sim = col1.button("▶️ Start", type="primary")
stop_sim = col2.button("⏹️ Stop")
reset_sim = col3.button("🔄 Reset")

if start_sim:
    st.session_state.simulation_running = True
if stop_sim:
    st.session_state.simulation_running = False
if reset_sim:
    st.session_state.historical_data = []
    st.session_state.simulation_running = False

# Main dashboard
tab1, tab2, tab3, tab4 = st.tabs(["📊 Live Dashboard", "📈 Analytics", "🔧 Cell Details", "📋 Task History"])

with tab1:
    # Task sequence management
    if st.session_state.simulation_running and st.session_state.task_sequence:
        if st.session_state.task_start_time is None:
            st.session_state.task_start_time = datetime.now()
        
        current_task = st.session_state.task_sequence[st.session_state.current_task_step]
        elapsed_time = (datetime.now() - st.session_state.task_start_time).total_seconds()
        
        # Check if current task is completed
        if elapsed_time >= current_task["params"]["time_seconds"]:
            current_task["completed"] = True
            st.session_state.current_task_step += 1
            st.session_state.task_start_time = datetime.now()
            
            # If all tasks completed, stop simulation
            if st.session_state.current_task_step >= len(st.session_state.task_sequence):
                st.session_state.simulation_running = False
                st.session_state.current_task_step = 0
                st.session_state.task_start_time = None
    
    # Display current task info
    if st.session_state.task_sequence and st.session_state.current_task_step < len(st.session_state.task_sequence):
        current_task = st.session_state.task_sequence[st.session_state.current_task_step]
        elapsed_time = (datetime.now() - st.session_state.task_start_time).total_seconds() if st.session_state.task_start_time else 0
        remaining_time = max(0, current_task["params"]["time_seconds"] - elapsed_time)
        
        st.markdown(f"""
        <div class="task-info">
            <h4>🔄 Current Task: {current_task['type']}</h4>
            <p><strong>Progress:</strong> {elapsed_time:.1f}s / {current_task['params']['time_seconds']}s</p>
            <p><strong>Remaining:</strong> {remaining_time:.1f}s</p>
            <p><strong>Step:</strong> {st.session_state.current_task_step + 1} of {len(st.session_state.task_sequence)}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Progress bar for current task
        progress = min(1.0, elapsed_time / current_task["params"]["time_seconds"])
        st.progress(progress)
    
    if st.session_state.simulation_running:
        # Update simulation
        for cell_key, cell_data in st.session_state.cells_data.items():
            st.session_state.cells_data[cell_key] = simulate_battery_operation(
                cell_data, task_type, task_params
            )
        
        # Store historical data
        timestamp = datetime.now()
        for cell_key, cell_data in st.session_state.cells_data.items():
            st.session_state.historical_data.append({
                "timestamp": timestamp,
                "cell": cell_key,
                "voltage": cell_data["voltage"],
                "current": cell_data["current"],
                "temperature": cell_data["temp"],
                "soc": cell_data["soc"],
                "capacity": cell_data["capacity"],
                "status": cell_data["status"]
            })
    
    # Download CSV button in live dashboard
    if st.session_state.historical_data:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col3:
            df_download = pd.DataFrame(st.session_state.historical_data)
            csv = df_download.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"live_battery_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                type="secondary"
            )
    
    # Display current status
    st.subheader("🔋 System Status")
    
    # Overall metrics
    col1, col2, col3, col4 = st.columns(4)
    
    avg_voltage = np.mean([cell["voltage"] for cell in st.session_state.cells_data.values()])
    total_current = sum([cell["current"] for cell in st.session_state.cells_data.values()])
    avg_temp = np.mean([cell["temp"] for cell in st.session_state.cells_data.values()])
    avg_soc = np.mean([cell["soc"] for cell in st.session_state.cells_data.values()])
    
    col1.metric("Avg Voltage", f"{avg_voltage:.2f} V", f"{avg_voltage-3.5:.2f}")
    col2.metric("Total Current", f"{total_current:.2f} A", f"{total_current:.2f}")
    col3.metric("Avg Temperature", f"{avg_temp:.1f} °C", f"{avg_temp-30:.1f}")
    col4.metric("Avg SOC", f"{avg_soc:.1f} %", f"{avg_soc-50:.1f}")
    
    # Individual cell status with new theme
    st.subheader("📱 Individual Cells")
    
    cols = st.columns(min(len(st.session_state.cells_data), 3))
    for idx, (cell_key, cell_data) in enumerate(st.session_state.cells_data.items()):
        col = cols[idx % 3]
        
        with col:
            # Dynamic card styling based on status
            card_class = {
                "CHARGING": "cell-card-charging",
                "DISCHARGING": "cell-card-discharging",
                "IDLE": "cell-card-idle"
            }.get(cell_data["status"], "cell-card")
            
            st.markdown(f"""
            <div class="cell-card {card_class}">
                <div class="cell-title">{cell_key.replace('_', ' ').title()}</div>
                <div class="cell-metric">
                    <span>Type:</span>
                    <span class="cell-metric-value">{cell_data.get('type', 'Unknown').upper()}</span>
                </div>
                <div class="cell-metric">
                    <span>Status:</span>
                    <span class="cell-metric-value">{cell_data['status']}</span>
                </div>
                <div class="cell-metric">
                    <span>Voltage:</span>
                    <span class="cell-metric-value">{cell_data['voltage']:.2f} V</span>
                </div>
                <div class="cell-metric">
                    <span>Current:</span>
                    <span class="cell-metric-value">{cell_data['current']:.2f} A</span>
                </div>
                <div class="cell-metric">
                    <span>SOC:</span>
                    <span class="cell-metric-value">{cell_data['soc']:.1f} %</span>
                </div>
                <div class="cell-metric">
                    <span>Temperature:</span>
                    <span class="cell-metric-value">{cell_data['temp']:.1f} °C</span>
                </div>
                <div class="cell-metric">
                    <span>Health:</span>
                    <span class="cell-metric-value">{cell_data['health']:.1f} %</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # SOC Progress bar with custom styling
            soc_color = "#28a745" if cell_data['soc'] > 50 else "#ffc107" if cell_data['soc'] > 20 else "#dc3545"
            st.markdown(f"""
            <div style="background-color: rgba(255,255,255,0.3); border-radius: 10px; padding: 5px; margin-top: 10px;">
                <div style="background-color: {soc_color}; height: 10px; border-radius: 5px; width: {cell_data['soc']}%;"></div>
            </div>
            """, unsafe_allow_html=True)

with tab2:
    st.subheader("📈 Performance Analytics")
    
    if st.session_state.historical_data:
        df = pd.DataFrame(st.session_state.historical_data)
        
        # Time series plots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Voltage vs Time', 'Current vs Time', 'Temperature vs Time', 'SOC vs Time'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        colors = px.colors.qualitative.Plotly
        
        for idx, cell in enumerate(df['cell'].unique()):
            cell_df = df[df['cell'] == cell]
            color = colors[idx % len(colors)]
            
            fig.add_trace(
                go.Scatter(x=cell_df['timestamp'], y=cell_df['voltage'], 
                          name=f'{cell} Voltage', line=dict(color=color)),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=cell_df['timestamp'], y=cell_df['current'], 
                          name=f'{cell} Current', line=dict(color=color)),
                row=1, col=2
            )
            fig.add_trace(
                go.Scatter(x=cell_df['timestamp'], y=cell_df['temperature'], 
                          name=f'{cell} Temp', line=dict(color=color)),
                row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=cell_df['timestamp'], y=cell_df['soc'], 
                          name=f'{cell} SOC', line=dict(color=color)),
                row=2, col=2
            )
        
        fig.update_layout(height=600, showlegend=True, title_text="Battery Performance Over Time")
        fig.update_xaxes(title_text="Time")
        fig.update_yaxes(title_text="Voltage (V)", row=1, col=1)
        fig.update_yaxes(title_text="Current (A)", row=1, col=2)
        fig.update_yaxes(title_text="Temperature (°C)", row=2, col=1)
        fig.update_yaxes(title_text="SOC (%)", row=2, col=2)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary statistics
        st.subheader("📊 Summary Statistics")
        summary_stats = df.groupby('cell').agg({
            'voltage': ['mean', 'min', 'max', 'std'],
            'current': ['mean', 'min', 'max', 'std'],
            'temperature': ['mean', 'min', 'max', 'std'],
            'soc': ['mean', 'min', 'max', 'std']
        }).round(3)
        
        st.dataframe(summary_stats, use_container_width=True)
    else:
        st.info("Start the simulation to see analytics data!")

with tab3:
    st.subheader("🔧 Detailed Cell Information")
    
    for cell_key, cell_data in st.session_state.cells_data.items():
        with st.expander(f"{cell_key.replace('_', ' ').title()} - {cell_data.get('type', 'Unknown').upper()}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Current Values:**")
                st.write(f"Voltage: {cell_data['voltage']:.3f} V")
                st.write(f"Current: {cell_data['current']:.3f} A")
                st.write(f"Temperature: {cell_data['temp']:.1f} °C")
                st.write(f"Capacity: {cell_data['capacity']:.3f} Wh")
                st.write(f"SOC: {cell_data['soc']:.1f} %")
                st.write(f"Health: {cell_data['health']:.1f} %")
            
            with col2:
                st.write("**Specifications:**")
                st.write(f"Min Voltage: {cell_data['min_voltage']:.1f} V")
                st.write(f"Max Voltage: {cell_data['max_voltage']:.1f} V")
                st.write(f"Cell Type: {cell_data.get('type', 'Unknown').upper()}")
                st.write(f"Status: {cell_data['status']}")
            
            # Individual cell chart
            if st.session_state.historical_data:
                cell_history = [d for d in st.session_state.historical_data if d['cell'] == cell_key]
                if cell_history:
                    df_cell = pd.DataFrame(cell_history)
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df_cell['timestamp'], 
                        y=df_cell['voltage'],
                        mode='lines',
                        name='Voltage',
                        line=dict(color='blue')
                    ))
                    
                    fig.add_hline(y=cell_data['min_voltage'], line_dash="dash", 
                                 line_color="red", annotation_text="Min Voltage")
                    fig.add_hline(y=cell_data['max_voltage'], line_dash="dash", 
                                 line_color="green", annotation_text="Max Voltage")
                    
                    fig.update_layout(
                        title=f"{cell_key} Voltage History",
                        xaxis_title="Time",
                        yaxis_title="Voltage (V)",
                        height=300
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("📋 Task Configuration & History")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Current Task Configuration:**")
        st.json({
            "task_type": task_type,
            "parameters": task_params,
            "simulation_running": st.session_state.simulation_running
        })
    
    with col2:
        st.write("**System Information:**")
        st.write(f"Number of Cells: {len(st.session_state.cells_data)}")
        st.write(f"Data Points Collected: {len(st.session_state.historical_data)}")
        st.write(f"Simulation Status: {'Running' if st.session_state.simulation_running else 'Stopped'}")
    
    # Export data option
    if st.session_state.historical_data:
        st.subheader("💾 Export Data")
        
        export_format = st.selectbox("Export Format", ["CSV", "JSON"])
        
        if st.button("📥 Download Data"):
            df_export = pd.DataFrame(st.session_state.historical_data)
            
            if export_format == "CSV":
                csv = df_export.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"battery_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                json_str = df_export.to_json(orient='records', indent=2)
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name=f"battery_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

# Auto-refresh for live simulation
if st.session_state.simulation_running:
    time.sleep(1)
    st.rerun()

# Footer
st.markdown("---")
st.markdown("🔋 **Battery Management System** - Real-time monitoring and simulation dashboard")