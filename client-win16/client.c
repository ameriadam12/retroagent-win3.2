/* RetroAgent Win16 串口客户端 —— 连 COM1,发 "ASK <输入>\n",轮询读回复显示。
   用 WM_TIMER 轮询(避开 EnableCommNotification 的复杂性)。GBK 字节透传。 */
#define STRICT
#include <windows.h>
#include <string.h>

#define IDC_INPUT  101
#define IDC_OUT    102
#define IDC_SEND   103
#define IDT_POLL   1

static int  comId = -1;
static HWND hInput, hOutput;
static char gBuf[1200];

static void OutText(char *s, int len) {
    int old, n, i;
    old = GetWindowTextLength(hOutput);
    SendMessage(hOutput, EM_SETSEL, old, old);
    while (len > 0) {
        n = (len > 1100) ? 1100 : len;
        for (i = 0; i < n; i++) gBuf[i] = s[i];
        gBuf[n] = 0;
        SendMessage(hOutput, EM_REPLACESEL, 0, (LPARAM)(LPSTR)gBuf);
        s += n; len -= n;
    }
}

static void DoSend(void) {
    int len;
    if (comId < 0) { OutText("[COM1 not open]\r\n", 17); return; }
    len = GetWindowText(hInput, gBuf, 1000);
    if (len <= 0) return;
    WriteComm(comId, "ASK ", 4);
    WriteComm(comId, gBuf, len);
    WriteComm(comId, "\n", 1);
    OutText("> ", 2);
    OutText(gBuf, len);
    OutText("\r\n", 2);
    SetWindowText(hInput, "");
}

static void DoPoll(void) {
    COMSTAT cs;
    int n, want;
    if (comId < 0) return;
    GetCommError(comId, &cs);
    while (cs.cbInQue > 0) {
        want = (cs.cbInQue < 1000) ? cs.cbInQue : 1000;
        n = ReadComm(comId, gBuf, want);
        if (n <= 0) break;
        OutText(gBuf, n);
        GetCommError(comId, &cs);
    }
}

static LRESULT CALLBACK WndProc(HWND h, UINT m, WPARAM w, LPARAM l) {
    switch (m) {
    case WM_CREATE: {
        LPCREATESTRUCT cs = (LPCREATESTRUCT)l;
        hOutput = CreateWindow("EDIT", "",
            WS_CHILD|WS_VISIBLE|WS_BORDER|WS_VSCROLL|ES_MULTILINE|ES_AUTOVSCROLL|ES_READONLY,
            10, 10, 460, 240, h, (HMENU)IDC_OUT, cs->hInstance, NULL);
        hInput = CreateWindow("EDIT", "",
            WS_CHILD|WS_VISIBLE|WS_BORDER|ES_AUTOHSCROLL,
            10, 260, 350, 24, h, (HMENU)IDC_INPUT, cs->hInstance, NULL);
        CreateWindow("BUTTON", "Send ->",
            WS_CHILD|WS_VISIBLE|BS_DEFPUSHBUTTON,
            370, 260, 100, 24, h, (HMENU)IDC_SEND, cs->hInstance, NULL);
        comId = OpenComm("COM1", 4096, 4096);
        if (comId < 0) {
            OutText("[COM1 open failed]\r\n", 21);
        } else {
            DCB dcb;
            memset(&dcb, 0, sizeof(dcb));
            dcb.Id = comId;
            BuildCommDCB("COM1:9600,n,8,1", &dcb);
            SetCommState(&dcb);
            SetTimer(h, IDT_POLL, 200, NULL);
            OutText("RetroAgent ready. Type and Send.\r\n", 34);
        }
        SetFocus(hInput);
        return 0;
    }
    case WM_COMMAND:
        if (LOWORD(w) == IDC_SEND) { DoSend(); return 0; }
        break;
    case WM_TIMER:
        if (w == IDT_POLL) { DoPoll(); return 0; }
        break;
    case WM_DESTROY:
        if (comId >= 0) { KillTimer(h, IDT_POLL); CloseComm(comId); }
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProc(h, m, w, l);
}

int PASCAL WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cmd, int show) {
    WNDCLASS wc;
    MSG msg;
    HWND h;
    MessageBox(NULL, "WinMain", "DBG", MB_OK);
    memset(&wc, 0, sizeof(wc));
    wc.style = CS_HREDRAW | CS_VREDRAW;
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hi;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wc.lpszClassName = "RetroAgent";
    if (!RegisterClass(&wc)) return 0;
    h = CreateWindow("RetroAgent", "RetroAgent over COM1",
        WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 500, 360,
        NULL, NULL, hi, NULL);
    if (!h) return 0;
    ShowWindow(h, show);
    UpdateWindow(h);
    while (GetMessage(&msg, NULL, 0, 0)) {
        if (!IsDialogMessage(h, &msg)) {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
    }
    return msg.wParam;
}
