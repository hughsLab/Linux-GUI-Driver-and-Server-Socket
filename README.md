# Linux-GUI-Driver-and-Server-Socket

Files in this repository are for the software to monitor and display the interrogation of a battery's BMS. The driver file (mod_ID1) interrogates the battery's BMS, then passes the data to the GUI for user control and to the network. The server socket file receives TCP packets enveloped as the MODbus word from the battery's BMS. The server socket is hosted on a VM on a private network. The socket server then converts from TCP to UDP, which can be easily accepted by OpenRVDAS.
![image](https://github.com/user-attachments/assets/d2a73756-a9f7-4999-a208-463f40c24fb7)
