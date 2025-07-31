import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import time
import random
from datetime import datetime, timedelta
import io

# Page configuration
st.set_page_config(
    page_title="Battery Management System",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for attractive light UI
st.markdown("""
<style>
    /* Main styling */
    .main > div {
        padding-top: 2rem;
    }
    
    /* Header styling */
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Metric cards */
    .metric-container {
        background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
        border: 1px solid #e9ecef;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .metric-container:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    
    /* Status badges */
    .status-badge {
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        text-align: center;
        margin: 0.2rem;
        display: inline-block;
        min-width: 80px;
    }
    
    .status-excellent { 
        background: linear-gradient(135deg, #28a745, #20c997);
        color: white;
        box-shadow: 0 2px 4px rgba(40, 167, 69, 0.3);
    }
    .status-good { 
        background: linear-gradient(135deg, #17a2b8, #20c997);
        color: white;
        box-shadow: 0 2px 4px rgba(23, 162, 184, 0.3);
    }
    .status-normal { 
        background: linear-gradient(135deg, #6c757d, #adb5bd);
        color: white;
        box-shadow: 0 2px 4px rgba(108, 117, 125, 0.3);
    }
    .status-warning { 
        background: linear-gradient(135deg, #ffc107, #fd7e14);
        color: #212529;
        box-shadow: 0 2px 4px rgba(255, 193, 7, 0.3);
    }
    .status-critical { 
        background: linear-gradient(135deg, #dc3545, #e74c3c);
        color: white;
        box-shadow: 0 2px 4px rgba(220, 53, 69, 0.3);
    }
    .status-danger { 
        background: linear-gradient(135deg, #721c24, #dc3545);
        color: white;
        box-shadow: 0 2px 4px rgba(114, 28, 36, 0.3);
    }
    
    /* Card styling */
    .info-card {
        background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
        border: 1px solid #dee2e6;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8f9fa 0%, #ffffff 100%);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
    }
    
    /* Table styling */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #495057;
        border-bottom: 3px solid #667eea;
        padding-bottom: 0.5rem;
        margin: 2rem 0 1rem 0;
    }
    
    /* Alert boxes */
    .alert-box {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid;
    }
    
    .alert-info {
        background-color: #d1ecf1;
        border-color: #17a2b8;
        color: #0c5460;
    }
    
    .alert-warning {
        background-color: #fff3cd;
        border-color: #ffc107;
        color: #856404;
    }
    
    .alert-success {
        background-color: #d4edda;
        border-color: #28a745;
        color: #155724;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'cells_data' not in st.session_state:
    st.session_state.cells_data = {}
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False
if 'historical_data' not in st.session_state:
    st.session_state.historical_data = []
if 'data_points' not in st.session_state:
    st.session_state.data_points = []

def calculate_soc(voltage, cell_type):
    """Calculate State of Charge based on voltage and cell type"""
    voltage_ranges = {
        "lfp": (2.5, 3.65),
        "nmc": (3.0, 4.2),
        "nimh": (1.0, 1.4),
        "lead-acid": (1.8, 2.1)
    }
    
    min_v, max_v = voltage_ranges.get(cell_type.lower(), (3.0, 4.2))
    soc = ((voltage - min_v) / (max_v - min_v)) * 100
    return max(0, min(100, soc))

def calculate_battery_health(voltage, current, temp, soc, cell_type):
    """Enhanced battery health calculation with more realistic parameters"""
    health_score = 100
    
    # Temperature impact (more realistic ranges)
    if temp > 50:
        health_score -= min(30, (temp - 50) * 3)  # Severe penalty above 50°C
    elif temp > 40:
        health_score -= (temp - 40) * 1.5  # Moderate penalty 40-50°C
    elif temp < 0:
        health_score -= min(25, abs(temp) * 2)  # Cold penalty
    elif temp < 10:
        health_score -= (10 - temp) * 0.8  # Mild cold penalty
    
    # Voltage impact based on cell type
    optimal_voltages = {
        "lfp": 3.3,
        "nmc": 3.7,
        "nimh": 1.25,
        "lead-acid": 2.0
    }
    
    optimal_v = optimal_voltages.get(cell_type.lower(), 3.7)
    voltage_deviation = abs(voltage - optimal_v)
    health_score -= min(20, voltage_deviation * 15)
    
    # Current impact (realistic discharge/charge rates)
    abs_current = abs(current)
    if abs_current > 8:
        health_score -= min(25, (abs_current - 8) * 3)
    elif abs_current > 5:
        health_score -= (abs_current - 5) * 1.5
    
    # SOC impact (battery stress at extremes)
    if soc < 10:
        health_score -= (10 - soc) * 2
    elif soc > 95:
        health_score -= (soc - 95) * 1.5
    elif soc < 20:
        health_score -= (20 - soc) * 0.5
    elif soc > 90:
        health_score -= (soc - 90) * 0.8
    
    # Add some randomness for realistic variation
    health_score += random.uniform(-2, 2)
    
    return max(0, min(100, health_score))

def get_detailed_cell_status(health, temp, voltage, soc, cell_type):
    """Get detailed cell status with suggestions"""
    suggestions = []
    
    # Health-based status
    if health >= 95:
        status = "Excellent"
        status_class = "status-excellent"
    elif health >= 85:
        status = "Good"
        status_class = "status-good"
    elif health >= 70:
        status = "Normal"
        status_class = "status-normal"
        suggestions.append("Monitor regularly")
    elif health >= 50:
        status = "Warning"
        status_class = "status-warning"
        suggestions.append("Check cell parameters")
    elif health >= 30:
        status = "Critical"
        status_class = "status-critical"
        suggestions.append("Immediate attention required")
    else:
        status = "Danger"
        status_class = "status-danger"
        suggestions.append("Replace cell immediately")
    
    # Temperature-based suggestions
    if temp > 45:
        suggestions.append("Cool down the battery")
    elif temp < 5:
        suggestions.append("Warm up the battery")
    
    # SOC-based suggestions
    if soc < 15:
        suggestions.append("Charge battery soon")
    elif soc > 95:
        suggestions.append("Avoid overcharging")
    
    # Voltage-based suggestions
    optimal_voltages = {
        "lfp": 3.3,
        "nmc": 3.7,
        "nimh": 1.25,
        "lead-acid": 2.0
    }
    optimal_v = optimal_voltages.get(cell_type.lower(), 3.7)
    if abs(voltage - optimal_v) > 0.3:
        suggestions.append("Check voltage regulation")
    
    return status, status_class, suggestions

def create_download_data():
    """Create comprehensive data for CSV download"""
    download_data = []
    timestamp = datetime.now()
    
    for cell_key, cell_data in st.session_state.cells_data.items():
        status, _, suggestions = get_detailed_cell_status(
            cell_data["health"], cell_data["temp"], 
            cell_data["voltage"], cell_data["soc"], cell_data["type"]
        )
        
        download_data.append({
            "Timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Cell_ID": cell_key,
            "Cell_Type": cell_data["type"],
            "Voltage_V": round(cell_data["voltage"], 3),
            "Current_A": round(cell_data["current"], 3),
            "Temperature_C": round(cell_data["temp"], 1),
            "SOC_Percent": round(cell_data["soc"], 1),
            "Health_Percent": round(cell_data["health"], 1),
            "Capacity_Wh": round(cell_data["capacity"], 2),
            "Status": status,
            "Suggestions": "; ".join(suggestions) if suggestions else "None"
        })
    
    return pd.DataFrame(download_data)

# Main title with enhanced styling
st.markdown('<h1 class="main-header">🔋 Advanced Battery Management System</h1>', unsafe_allow_html=True)

# Top action bar
col_actions1, col_actions2, col_actions3, col_actions4 = st.columns([2, 2, 2, 2])

with col_actions1:
    if st.button("🚀 Start Simulation", use_container_width=True):
        st.session_state.simulation_running = True
        st.success("Simulation started!")

with col_actions2:
    if st.button("⏹️ Stop Simulation", use_container_width=True):
        st.session_state.simulation_running = False
        st.info("Simulation stopped!")

with col_actions3:
    if st.button("🔄 Reset Data", use_container_width=True):
        st.session_state.historical_data = []
        st.session_state.data_points = []
        st.warning("Data reset!")

with col_actions4:
    if st.session_state.cells_data:
        csv_data = create_download_data()
        csv_buffer = io.StringIO()
        csv_data.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="📥 Download CSV",
            data=csv_buffer.getvalue(),
            file_name=f"battery_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# Sidebar for cell configuration
st.sidebar.markdown("### ⚙️ Cell Configuration")

# Number of cells with better styling
num_cells = st.sidebar.slider("🔢 Number of Cells", min_value=1, max_value=16, value=8)

# Simulation settings
st.sidebar.markdown("### 🎮 Simulation Settings")
simulation_speed = st.sidebar.slider("⚡ Update Speed (Hz)", 0.1, 3.0, 1.0, 0.1)
noise_level = st.sidebar.slider("🌊 Parameter Variation", 0.0, 2.0, 0.5, 0.1)

# Cell configuration section
st.sidebar.markdown("### 🔋 Individual Cell Settings")

# Initialize or update cells data
for i in range(1, num_cells + 1):
    cell_key = f"cell_{i}"
    
    if cell_key not in st.session_state.cells_data:
        # Initialize with more varied parameters for realistic demonstration
        base_temp = random.uniform(20, 35)
        base_voltage = random.uniform(3.0, 4.0)
        base_current = random.uniform(-2, 2)
        
        st.session_state.cells_data[cell_key] = {
            "type": random.choice(["NMC", "LFP"]),
            "voltage": base_voltage,
            "current": base_current,
            "temp": base_temp,
            "capacity": 0.0,
            "soc": 50.0,
            "health": random.uniform(60, 100)  # More varied initial health
        }
    
    with st.sidebar.expander(f"🔋 Cell {i} Configuration", expanded=False):
        cell_type = st.selectbox(
            "Cell Type",
            ["NMC", "LFP", "NiMH", "Lead-Acid"],
            key=f"type_{i}",
            index=["NMC", "LFP", "NiMH", "Lead-Acid"].index(st.session_state.cells_data[cell_key]["type"])
        )
        
        voltage = st.slider(
            "Voltage (V)",
            min_value=0.0, max_value=5.0, value=st.session_state.cells_data[cell_key]["voltage"],
            step=0.01, key=f"voltage_{i}"
        )
        
        current = st.slider(
            "Current (A)",
            min_value=-15.0, max_value=15.0, value=st.session_state.cells_data[cell_key]["current"],
            step=0.1, key=f"current_{i}"
        )
        
        temp = st.slider(
            "Temperature (°C)",
            min_value=-10.0, max_value=70.0, value=st.session_state.cells_data[cell_key]["temp"],
            step=0.5, key=f"temp_{i}"
        )
        
        # Update cell data
        st.session_state.cells_data[cell_key].update({
            "type": cell_type,
            "voltage": voltage,
            "current": current,
            "temp": temp,
            "capacity": round(voltage * abs(current), 2),
            "soc": calculate_soc(voltage, cell_type),
            "health": calculate_battery_health(voltage, current, temp, calculate_soc(voltage, cell_type), cell_type)
        })

# Remove excess cells if number decreased
cells_to_remove = [key for key in st.session_state.cells_data.keys() 
                  if int(key.split('_')[1]) > num_cells]
for key in cells_to_remove:
    del st.session_state.cells_data[key]

# Main dashboard metrics
st.markdown('<div class="section-header">📊 System Overview</div>', unsafe_allow_html=True)

if st.session_state.cells_data:
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Calculate overall metrics
    total_voltage = sum(cell["voltage"] for cell in st.session_state.cells_data.values())
    avg_temp = np.mean([cell["temp"] for cell in st.session_state.cells_data.values()])
    avg_soc = np.mean([cell["soc"] for cell in st.session_state.cells_data.values()])
    avg_health = np.mean([cell["health"] for cell in st.session_state.cells_data.values()])
    total_capacity = sum(cell["capacity"] for cell in st.session_state.cells_data.values())
    
    with col1:
        st.metric("🔋 Pack Voltage", f"{total_voltage:.1f} V", 
                 f"{random.uniform(-0.1, 0.1):.2f}" if st.session_state.simulation_running else None)
    
    with col2:
        temp_delta = f"{random.uniform(-1, 1):.1f}" if st.session_state.simulation_running else None
        st.metric("🌡️ Avg Temperature", f"{avg_temp:.1f} °C", temp_delta)
    
    with col3:
        soc_delta = f"{random.uniform(-2, 2):.1f}" if st.session_state.simulation_running else None
        st.metric("⚡ Avg SOC", f"{avg_soc:.1f} %", soc_delta)
    
    with col4:
        health_delta = f"{random.uniform(-0.5, 0.5):.1f}" if st.session_state.simulation_running else None
        st.metric("💚 Avg Health", f"{avg_health:.1f} %", health_delta)
    
    with col5:
        st.metric("🔌 Total Capacity", f"{total_capacity:.1f} Wh")

    # System status alerts
    if avg_health < 70:
        st.markdown('<div class="alert-box alert-warning">⚠️ <strong>System Warning:</strong> Average battery health is below optimal levels. Consider maintenance.</div>', unsafe_allow_html=True)
    elif avg_temp > 40:
        st.markdown('<div class="alert-box alert-warning">🌡️ <strong>Temperature Alert:</strong> System temperature is elevated. Check cooling systems.</div>', unsafe_allow_html=True)
    elif avg_soc < 20:
        st.markdown('<div class="alert-box alert-warning">🔋 <strong>Low Battery:</strong> System SOC is low. Charging recommended.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-box alert-success">✅ <strong>System Status:</strong> All parameters within normal ranges.</div>', unsafe_allow_html=True)

    # Enhanced cell status table
    st.markdown('<div class="section-header">🔍 Detailed Cell Analysis</div>', unsafe_allow_html=True)
    
    # Create enhanced DataFrame
    cells_data_enhanced = []
    for key, data in st.session_state.cells_data.items():
        status, status_class, suggestions = get_detailed_cell_status(
            data['health'], data['temp'], data['voltage'], data['soc'], data['type']
        )
        
        cells_data_enhanced.append({
            "Cell ID": key,
            "Type": data["type"],
            "Voltage (V)": f"{data['voltage']:.3f}",
            "Current (A)": f"{data['current']:.2f}",
            "Temp (°C)": f"{data['temp']:.1f}",
            "SOC (%)": f"{data['soc']:.1f}",
            "Health (%)": f"{data['health']:.1f}",
            "Capacity (Wh)": f"{data['capacity']:.2f}",
            "Status": status,
            "Suggestions": "; ".join(suggestions[:2]) if suggestions else "None"  # Limit suggestions for table
        })
    
    df_enhanced = pd.DataFrame(cells_data_enhanced)
    
    # Display table with status highlighting
    st.dataframe(
        df_enhanced,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Cell ID": st.column_config.TextColumn("Cell ID", width="small"),
            "Status": st.column_config.TextColumn("Status", width="medium"),
            "Suggestions": st.column_config.TextColumn("Suggestions", width="large"),
        }
    )
    
    # Status distribution
    col_status1, col_status2 = st.columns(2)
    
    with col_status1:
        status_counts = {}
        for key, data in st.session_state.cells_data.items():
            status, _, _ = get_detailed_cell_status(
                data['health'], data['temp'], data['voltage'], data['soc'], data['type']
            )
            status_counts[status] = status_counts.get(status, 0) + 1
        
        if status_counts:
            fig_status = px.pie(
                values=list(status_counts.values()),
                names=list(status_counts.keys()),
                title="Cell Status Distribution",
                color_discrete_map={
                    'Excellent': '#28a745',
                    'Good': '#17a2b8',
                    'Normal': '#6c757d',
                    'Warning': '#ffc107',
                    'Critical': '#dc3545',
                    'Danger': '#721c24'
                }
            )
            fig_status.update_layout(height=300)
            st.plotly_chart(fig_status, use_container_width=True)
    
    with col_status2:
        # Health distribution histogram
        health_values = [cell["health"] for cell in st.session_state.cells_data.values()]
        fig_health_dist = px.histogram(
            x=health_values,
            nbins=10,
            title="Health Score Distribution",
            labels={'x': 'Health Score (%)', 'y': 'Number of Cells'},
            color_discrete_sequence=['#667eea']
        )
        fig_health_dist.update_layout(height=300)
        st.plotly_chart(fig_health_dist, use_container_width=True)
    
    # Enhanced visualizations
    st.markdown('<div class="section-header">📈 Real-time Parameter Monitoring</div>', unsafe_allow_html=True)
    
    # Create comprehensive monitoring charts
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # Voltage and Current comparison
        fig1 = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Cell Voltages (V)', 'Cell Currents (A)'),
            vertical_spacing=0.15
        )
        
        cells = list(st.session_state.cells_data.keys())
        voltages = [st.session_state.cells_data[cell]["voltage"] for cell in cells]
        currents = [st.session_state.cells_data[cell]["current"] for cell in cells]
        
        # Color code based on health
        voltage_colors = []
        current_colors = []
        for cell in cells:
            health = st.session_state.cells_data[cell]["health"]
            if health >= 85:
                color = '#28a745'
            elif health >= 70:
                color = '#17a2b8'
            elif health >= 50:
                color = '#ffc107'
            else:
                color = '#dc3545'
            voltage_colors.append(color)
            current_colors.append(color)
        
        fig1.add_trace(
            go.Bar(x=cells, y=voltages, name="Voltage", marker_color=voltage_colors),
            row=1, col=1
        )
        
        fig1.add_trace(
            go.Bar(x=cells, y=currents, name="Current", marker_color=current_colors),
            row=2, col=1
        )
        
        fig1.update_layout(height=500, showlegend=False, title_text="Electrical Parameters")
        st.plotly_chart(fig1, use_container_width=True)
    
    with col_chart2:
        # Temperature and Health monitoring
        fig2 = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Cell Temperatures (°C)', 'Cell Health (%)'),
            vertical_spacing=0.15
        )
        
        temps = [st.session_state.cells_data[cell]["temp"] for cell in cells]
        healths = [st.session_state.cells_data[cell]["health"] for cell in cells]
        
        fig2.add_trace(
            go.Scatter(x=cells, y=temps, mode='lines+markers', name="Temperature",
                      line=dict(color='orange', width=3), marker=dict(size=8)),
            row=1, col=1
        )
        
        # Health bars with color coding
        health_colors = []
        for health in healths:
            if health >= 85:
                health_colors.append('#28a745')
            elif health >= 70:
                health_colors.append('#17a2b8')
            elif health >= 50:
                health_colors.append('#ffc107')
            else:
                health_colors.append('#dc3545')
        
        fig2.add_trace(
            go.Bar(x=cells, y=healths, name="Health", marker_color=health_colors),
            row=2, col=1
        )
        
        fig2.update_layout(height=500, showlegend=False, title_text="Environmental & Health")
        st.plotly_chart(fig2, use_container_width=True)

# Live simulation with enhanced variations
if st.session_state.simulation_running:
    # Add current data to historical tracking
    current_time = datetime.now()
    
    # Store individual cell data points
    for cell_key, cell_data in st.session_state.cells_data.items():
        st.session_state.data_points.append({
            'timestamp': current_time,
            'cell_id': cell_key,
            'voltage': cell_data['voltage'],
            'current': cell_data['current'],
            'temperature': cell_data['temp'],
            'soc': cell_data['soc'],
            'health': cell_data['health']
        })
    
    # Add system averages to historical data
    st.session_state.historical_data.append({
        'timestamp': current_time,
        'avg_voltage': total_voltage / len(st.session_state.cells_data),
        'avg_temp': avg_temp,
        'avg_soc': avg_soc,
        'avg_health': avg_health,
        'total_capacity': total_capacity
    })
    
    # Keep only last 100 data points for performance
    if len(st.session_state.historical_data) > 100:
        st.session_state.historical_data = st.session_state.historical_data[-100:]
    if len(st.session_state.data_points) > 500:
        st.session_state.data_points = st.session_state.data_points[-500:]
    
    # Enhanced simulation with more realistic variations
    for cell_key in st.session_state.cells_data:
        cell = st.session_state.cells_data[cell_key]
        
        # Temperature variations (influenced by current)
        temp_variation = random.uniform(-noise_level, noise_level)
        if abs(cell["current"]) > 3:  # High current increases temperature
            temp_variation += abs(cell["current"]) * 0.1
        cell["temp"] += temp_variation
        cell["temp"] = max(-10, min(70, cell["temp"]))  # Bounds checking
        
        # Voltage variations (more realistic based on SOC and current)
        voltage_variation = random.uniform(-noise_level*0.02, noise_level*0.02)
        if cell["current"] < 0:  # Discharging
            voltage_variation -= abs(cell["current"]) * 0.002
        cell["voltage"] += voltage_variation
        cell["voltage"] = max(0.1, min(5.0, cell["voltage"]))
        
        # Current variations (simulate load changes)
        current_variation = random.uniform(-noise_level*0.5, noise_level*0.5)
        cell["current"] += current_variation
        cell["current"] = max(-15, min(15, cell["current"]))
        
        # Recalculate dependent values
        cell["soc"] = calculate_soc(cell["voltage"], cell["type"])
        cell["capacity"] = round(cell["voltage"] * abs(cell["current"]), 2)
        cell["health"] = calculate_battery_health(
            cell["voltage"], cell["current"], cell["temp"], cell["soc"], cell["type"]
        )
    
    # Auto-refresh with controlled timing
    time.sleep(1/simulation_speed)
    st.rerun()

# Historical trends display
if st.session_state.historical_data:
    st.markdown('<div class="section-header">📊 Historical Trends Analysis</div>', unsafe_allow_html=True)
    
    df_hist = pd.DataFrame(st.session_state.historical_data)
    
    # Create historical trends chart
    fig_hist = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Average Voltage Trend', 'Average Temperature Trend', 
                       'Average SOC Trend', 'Average Health Trend'),
        vertical_spacing=0.1,
        horizontal_spacing=0.1
    )
    
    fig_hist.add_trace(
        go.Scatter(x=df_hist['timestamp'], y=df_hist['avg_voltage'], 
                  name='Avg Voltage', line=dict(color='blue', width=2)),
        row=1, col=1
    )
    
    fig_hist.add_trace(
        go.Scatter(x=df_hist['timestamp'], y=df_hist['avg_temp'], 
                  name='Avg Temperature', line=dict(color='orange', width=2)),
        row=1, col=2
    )
    
    fig_hist.add_trace(
        go.Scatter(x=df_hist['timestamp'], y=df_hist['avg_soc'], 
                  name='Avg SOC', line=dict(color='green', width=2)),
        row=2, col=1
    )
    
    fig_hist.add_trace(
        go.Scatter(x=df_hist['timestamp'], y=df_hist['avg_health'], 
                  name='Avg Health', line=dict(color='purple', width=2)),
        row=2, col=2
    )
    
    fig_hist.update_layout(height=500, showlegend=False, title_text="System Performance Over Time")
    fig_hist.update_xaxes(title_text="Time")
    fig_hist.update_yaxes(title_text="Voltage (V)", row=1, col=1)
    fig_hist.update_yaxes(title_text="Temperature (°C)", row=1, col=2)
    fig_hist.update_yaxes(title_text="SOC (%)", row=2, col=1)
    fig_hist.update_yaxes(title_text="Health (%)", row=2, col=2)
    
    st.plotly_chart(fig_hist, use_container_width=True)
    
    # Individual cell temperature trends
    if st.session_state.data_points:
        st.markdown("### 🌡️ Individual Cell Temperature Monitoring")
        
        df_cells = pd.DataFrame(st.session_state.data_points)
        
        # Temperature trends for each cell
        fig_temp_trends = go.Figure()
        
        for cell_id in df_cells['cell_id'].unique():
            cell_data = df_cells[df_cells['cell_id'] == cell_id]
            fig_temp_trends.add_trace(
                go.Scatter(
                    x=cell_data['timestamp'],
                    y=cell_data['temperature'],
                    mode='lines',
                    name=f'{cell_id} Temperature',
                    line=dict(width=2)
                )
            )
        
        fig_temp_trends.update_layout(
            title="Individual Cell Temperature Trends",
            xaxis_title="Time",
            yaxis_title="Temperature (°C)",
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_temp_trends, use_container_width=True)

# Footer with system information
st.markdown("---")
col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    st.markdown("**🔋 Battery Management System**")
    st.markdown("Advanced monitoring and simulation")

with col_footer2:
    if st.session_state.cells_data:
        st.markdown(f"**📊 System Status**")
        st.markdown(f"Cells: {len(st.session_state.cells_data)} | "
                   f"Simulation: {'Running' if st.session_state.simulation_running else 'Stopped'}")

with col_footer3:
    st.markdown("**📈 Data Points**")
    st.markdown(f"Historical: {len(st.session_state.historical_data)} | "
               f"Cell Data: {len(st.session_state.data_points)}")

# Status indicator
if st.session_state.simulation_running:
    st.markdown(
        '<div style="position: fixed; top: 80px; right: 20px; background: #28a745; color: white; '
        'padding: 8px 16px; border-radius: 20px; font-weight: bold; z-index: 999;">'
        '🟢 LIVE</div>', 
        unsafe_allow_html=True
    )