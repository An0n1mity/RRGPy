import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from scipy import interpolate
from matplotlib.widgets import Slider, Button
import mpldatacursor

is_playing = False
marker_size = []
tail = 5
start_date, end_date = None, None

for i in range(tail):
    marker_size.append((i+1) * 10)

def get_line_points(x, y):
    # Interpolate a smooth curve through the scatter points
    tck, _ = interpolate.splprep([x, y], s=0)
    t = np.linspace(0, 1, 100)
    line_x, line_y = interpolate.splev(t, tck)
    return line_x, line_y

def get_status(x, y):
    if x < 100 and y < 100:
        return 'lagging'
    elif x > 100 and y > 100:
        return 'leading'
    elif x < 100 and y > 100:
        return 'improving'
    elif x > 100 and y < 100:
        return 'weakening'
    
def get_color(x, y):
    if get_status(x, y) == 'lagging':
        return 'red'
    elif get_status(x, y) == 'leading':
        return 'green'
    elif get_status(x, y) == 'improving':
        return 'blue'
    elif get_status(x, y) == 'weakening':
        return 'yellow'
    
# Retrieve historical prices 
period = '1y'
tickers = ['FOO.PA', 'HLT.PA', 'TNO.PA', 'BNK.PA', 'VIE.PA', 'VRLA.PA']
# 'symbol', 'name', 'sector', 'industry'
tickers_metadata_dict = {
    'symbol': [],
    'name': []
}

for i in range(len(tickers)):
    info = yf.Ticker(tickers[i]).info
    tickers_metadata_dict['symbol'].append(info['symbol'])
    tickers_metadata_dict['name'].append(info['longName'])

tickers_to_show = tickers

benchmark = '^STOXX'

tickers_data = yf.download(tickers, period=period, interval="1wk")['Adj Close']
benchmark_data = yf.download(benchmark, period=period, interval="1wk")['Adj Close']

stoxx = yf.download(benchmark, period=period, interval="1wk")['Adj Close']
window = 14

rs_tickers = []
rsr_tickers = []
rsr_roc_tickers = []
rsm_tickers = []

for i in range(len(tickers)):
    rs_tickers.append(100 * (tickers_data[tickers[i]]/ benchmark_data))
    rsr_tickers.append((100 + (rs_tickers[i] - rs_tickers[i].rolling(window=window).mean()) / rs_tickers[i].rolling(window=window).std(ddof=0)).dropna())
    rsr_roc_tickers.append(100 * ((rsr_tickers[i]/ rsr_tickers[i][1]) - 1))
    rsm_tickers.append((101 + ((rsr_roc_tickers[i] - rsr_roc_tickers[i].rolling(window=window).mean()) / rsr_roc_tickers[i].rolling(window=window).std(ddof=0))).dropna())
    rsr_tickers[i] = rsr_tickers[i][rsr_tickers[i].index.isin(rsm_tickers[i].index)]
    rsm_tickers[i] = rsm_tickers[i][rsm_tickers[i].index.isin(rsr_tickers[i].index)]

# Create scatter plot of JdK RS Ratio vs JdK RS Momentum
# Upper plot is JdK RS Ratio vs JdK RS Momentum and below is a table of the status of each ticker
fig, ax = plt.subplots(2, 1, figsize=(10, 10), gridspec_kw={'height_ratios': [3, 1]})
ax[0].set_title('RRG Indicator')
ax[0].set_xlabel('JdK RS Ratio')
ax[0].set_ylabel('JdK RS Momentum')

# Add horizontal and vertical lines to (100, 100) origin 
ax[0].axhline(y=100, color='k', linestyle='--')
ax[0].axvline(x=100, color='k', linestyle='--')

# Color each quadrant
ax[0].fill_between([94, 100], [94, 94], [100, 100], color='red', alpha=0.2)
ax[0].fill_between([100, 106], [94, 94], [100, 100], color='yellow', alpha=0.2)
ax[0].fill_between([100, 106], [100, 100], [106, 106], color='green', alpha=0.2)
ax[0].fill_between([94, 100], [100, 100], [106, 106], color='blue', alpha=0.2)
# Add text labels in each corner
ax[0].text(95, 105, 'Improving')
ax[0].text(105, 105, 'Leading')
ax[0].text(105, 95, 'Weakening')
ax[0].text(95, 95, 'Lagging')

ax[0].set_xlim(94, 106)
ax[0].set_ylim(94, 106)

ax[1].set_axis_off()
collabels = ['symbol', 'name', 'sector', 'industry', 'price', 'chg']

table = ax[1].table(cellText=[[''] * len(collabels)], colLabels=collabels, loc='center', colWidths=[0.1, 0.2, 0.2, 0.2, 0.1, 0.1])

for i in range(len(tickers)):
    table.add_cell(i+1, 0, width=0.1, height=0.1, text=tickers[i]) 
    #price 
    table.add_cell(i+1, 4, width=0.1, height=0.1, text=round(tickers_data[tickers[i]][-1], 2))
    # change in percentage
    table.add_cell(i+1, 5, width=0.1, height=0.1, text=round((tickers_data[tickers[i]][-1] - tickers_data[tickers[i]][-2]) / tickers_data[tickers[i]][-2] * 100, 2))

# Add a slider for the end date 
ax_end_date = plt.axes([0.25, 0.02, 0.65, 0.03])
slider_end_date = Slider(ax_end_date, 'Date', tail, len(rsr_tickers[0])-2, valinit=tail, valstep=1)
slider_end_date.valtext.set_text(rsr_tickers[0].index[slider_end_date.val])

def update_slider_end_date(val):
    slider_end_date.valtext.set_text(rsr_tickers[0].index[slider_end_date.val])

slider_end_date.on_changed(update_slider_end_date)

# get the real date from the slider value
start_date = rsr_tickers[0].index[0]
end_date = rsr_tickers[0].index[slider_end_date.val]

#  Add a slider for the tail 
ax_tail = plt.axes([0.25, 0.05, 0.65, 0.03])
slider_tail = Slider(ax_tail, 'Tail', 1, 10, valinit=5, valstep=1)

def update_slider_tail(val):
    global tail
    global marker_size
    # check if the end date - tail is less than the start date 
    if slider_end_date.val - slider_tail.val < slider_end_date.valmin:
        slider_tail.eventson = False
        slider_tail.set_val(tail)
        slider_tail.eventson = True
        return
    # Update the min of the end date slider 
    slider_end_date.valmin = slider_tail.val
    slider_end_date.ax.set_xlim(slider_tail.val, slider_end_date.valmax)
    tail = slider_tail.val
    marker_size = []
    for i in range(tail):
        marker_size.append(10 * (i+1))

slider_tail.on_changed(update_slider_tail)

# Add a button to play the animation 
ax_play = plt.axes([0.05, 0.02, 0.1, 0.04])
button_play = Button(ax_play, 'Play')

def update_button_play(event):
    global is_playing
    is_playing = not is_playing
    if is_playing:
        button_play.label.set_text('Pause')
    else:
        button_play.label.set_text('Play')

button_play.on_clicked(update_button_play)

# list of scatter plots for each ticker 
scatter_plots = [] 
# list of line plots for each ticker 
line_plots = []
# list of annotations for each ticker 
annotations = []

for i in range(len(tickers)):
    scatter_plots.append(ax[0].scatter([], []))
    line_plots.append(ax[0].plot([], [], color='k', alpha=0.2)[0]) 
    annotations.append(ax[0].annotate(tickers[i], (0, 0), fontsize=8))

# animation function. This is called sequentially 
def animate(i):
    global start_date, end_date
    if not is_playing:
        # take the value from the slider 
        end_date = rsr_tickers[0].index[slider_end_date.val]
        start_date = rsr_tickers[0].index[slider_end_date.val - tail]
    
    # if the end date is reached, reset the start and end date
    else:
        start_date += pd.to_timedelta(1,unit='w')
        end_date += pd.to_timedelta(1,unit='w')

        # update the slider 
        slider_end_date.eventson = False
        #slider_end_date.set_val((slider_end_date.val + 1)%slider_end_date.valmax)
        slider_end_date.eventson = True

    if end_date == rsr_tickers[0].index[-1]:
        start_date = rsr_tickers[0].index[0]
        end_date = start_date + pd.to_timedelta(tail,unit='w')

    for j in range(len(tickers)):
        # if ticker not to be displayed, skip it 
        if tickers[j] not in tickers_to_show:
            continue

        filtered_rsr_tickers = rsr_tickers[j].loc[(rsr_tickers[j].index > start_date) & (rsr_tickers[j].index <= end_date)]
        filtered_rsm_tickers = rsm_tickers[j].loc[(rsm_tickers[j].index > start_date) & (rsm_tickers[j].index <= end_date)]
        # Update the scatter
        color = get_color(filtered_rsr_tickers.values[-1], filtered_rsm_tickers.values[-1])
        scatter_plots[j] = ax[0].scatter(filtered_rsr_tickers.values, filtered_rsm_tickers.values, color=color, s=marker_size)
        # Update the line
        line_plots[j] = ax[0].plot(filtered_rsr_tickers.values, filtered_rsm_tickers.values, color='black', alpha=0.2)[0]
        # Update the annotation
        annotations[j] = ax[0].annotate(tickers[j], (filtered_rsr_tickers.values[-1], filtered_rsm_tickers.values[-1]))
        # Update the table cell price 
        table._cells[(j+1, 4)]._text.set_text(round(tickers_data[tickers[j]][start_date:end_date].values[-1], 2))
        # Update the table cell change 
        table._cells[(j+1, 5)]._text.set_text(round((tickers_data[tickers[j]][start_date:end_date].values[-1] - tickers_data[tickers[j]][start_date:end_date].values[-2]) / tickers_data[tickers[j]][start_date:end_date].values[-2] * 100, 2))

    return scatter_plots + line_plots + annotations + [table]

# call the animator. blit=True means only re-draw the parts that have changed.
anim = animation.FuncAnimation(fig, animate, frames=60, interval=100, blit=True)

plt.show()