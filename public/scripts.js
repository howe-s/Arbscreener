// Firebase Auth state observer
firebase.auth().onAuthStateChanged((user) => {
    if (user) {
        document.getElementById('login-btn').style.display = 'none';
        document.getElementById('logout-btn').style.display = 'block';
    } else {
        document.getElementById('login-btn').style.display = 'block';
        document.getElementById('logout-btn').style.display = 'none';
    }
});

$(document).ready(function() {
    fetchLogs();
    let arbitrageContainer = $('#arbitrage-opportunities');
    
    function showLoading() {
        arbitrageContainer.html(`
            <div class="col-12 text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden"></span>
                </div>
                <p>(Please do not refresh)</p>
            </div>
        `);
    }

    function fetchArbitrageData(formData) {
        showLoading();
        $.ajax({
            type: 'POST',
            url: '/landing_page_data',
            data: formData,
            success: function(data) {
                arbitrageContainer.empty();

                if (data.length > 0) {
                    data.forEach(opportunity => {
                        // Create card for each opportunity
                        let cardHTML = createOpportunityCard(opportunity);
                        arbitrageContainer.append(cardHTML);
                    });
                    updateTokenColors();
                } else {
                    arbitrageContainer.append('<p>No arbitrage opportunities found.</p>');
                }
                
                adjustCardWidths();
            },
            error: function(xhr, status, error) {
                arbitrageContainer.html('<p>An error occurred while fetching arbitrage data.</p>');
                console.error('Error fetching arbitrage data:', error);
            }
        });
    }

    function createOpportunityCard(opportunity) {
        return `
            <div id="arb-cards" class="col">
                <div class="card shadow-sm h-100">
                    <div class="card-header text-left">
                        <h5 class="card-title mb-0">Arbitrage Opportunity</h5>
                    </div>
                    <div class="card-body p-3">
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                ${createTableContent(opportunity)}
                            </table>
                        </div>
                    </div>
                </div>
            </div>`;
    }

    function createTableContent(opportunity) {
        const headers = ['Detail', opportunity.pair1, opportunity.pair2];
        if (opportunity.pair3) headers.push(opportunity.pair3);

        return `
            <thead>
                <tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr>
            </thead>
            <tbody>
                ${createTableRows(opportunity)}
            </tbody>`;
    }

    function createTableRows(opportunity) {
        const rows = [
            {
                label: 'Price',
                values: [
                    `$${opportunity.pair1_price_round}`,
                    `$${opportunity.pair2_price_round}`,
                    opportunity.pair3 ? `$${opportunity.pair3_price}` : null
                ]
            },
            // Add other rows similarly
        ];

        return rows.map(row => `
            <tr>
                <th>${row.label}</th>
                ${row.values.filter(v => v !== null).map(v => `<td>${v}</td>`).join('')}
            </tr>
        `).join('');
    }

    function fetchLogs() {
        $.ajax({
            type: 'GET',
            url: '/get_logs',
            success: function(logs) {
                let logWindow = $('#log-window');
                if (logs.length > 0) {
                    logWindow.removeClass('hidden');
                    logWindow.empty();
                    logs.forEach(log => {
                        logWindow.append($('<p>').text(log));
                    });
                    logWindow.scrollTop(logWindow[0].scrollHeight);
                }
            }
        });
    }

    function adjustCardWidths() {
        let cards = document.querySelectorAll('.card.shadow-sm');
        let maxWidth = 0;
        cards.forEach(card => {
            maxWidth = Math.max(maxWidth, card.offsetWidth);
        });
        cards.forEach(card => {
            card.style.minWidth = maxWidth + 'px';
        });
    }

    function updateTokenColors() {
        let tables = document.querySelectorAll('#arbitrage-opportunities table');
        const colors = ['#FFD700', '#FF6347', '#40E0D0'];

        tables.forEach(table => {
            let colorIndex = 0;
            let addressMap = {};
            
            table.querySelectorAll('td[data-address]').forEach(td => {
                let address = td.getAttribute('data-address');
                if (!addressMap[address]) addressMap[address] = [];
                addressMap[address].push(td);
            });

            for (let address in addressMap) {
                if (addressMap[address].length > 1) {
                    addressMap[address].slice(0, 2).forEach(td => {
                        td.style.color = colors[colorIndex];
                    });
                    colorIndex = (colorIndex + 1) % colors.length;
                }
            }
        });
    }

    // Event Listeners
    $('form').on('submit', function(e) {
        e.preventDefault();
        var formData = $(this).serialize();
        fetchArbitrageData(formData);
        fetchLogs();
    });

    $('#login-btn').click(() => {
        // Implement Firebase login
    });

    $('#logout-btn').click(() => {
        firebase.auth().signOut();
    });

    setInterval(fetchLogs, 1000);

    setTimeout(() => {
        document.body.classList.add('loaded');
    }, 100);
}); 