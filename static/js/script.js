async function sendText() {
    const textInput = document.getElementById('textInput').value;

    const response = await fetch('/process-text', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: textInput }),
    });

    const result = await response.json();
    document.getElementById('result').innerText = JSON.stringify(result, null, 2);
}
