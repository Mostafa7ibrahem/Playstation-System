// زيادة أو تقليل الوقت بمقدار 15 دقيقة (0.25 ساعة)
document.getElementById('increase-time').addEventListener('click', function() {
    let timeInput = document.getElementById('total_time');
    let currentTime = parseFloat(timeInput.value) || 0;
    timeInput.value = (currentTime + 0.25).toFixed(2);
});

document.getElementById('decrease-time').addEventListener('click', function() {
    let timeInput = document.getElementById('total_time');
    let currentTime = parseFloat(timeInput.value) || 0;
    if (currentTime >= 0.25) {
        timeInput.value = (currentTime - 0.25).toFixed(2);
    }
});

// حساب إجمالي الأرباح
function calculateTotalEarnings() {
    let earnings = document.querySelectorAll('td:nth-child(3)');
    let total = 0;
    earnings.forEach(earning => {
        total += parseFloat(earning.textContent) || 0;
    });
    document.getElementById('total-earnings').textContent = total.toFixed(2);
}

// تحديث الأرباح عند تحميل الصفحة
window.onload = calculateTotalEarnings;