# Run with: vhs docs/demo.tape
Output docs/demo.gif

Set Shell bash
Set FontSize 14
Set Width 960
Set Height 520
Set Padding 24
Set Theme "Catppuccin Mocha"
Set TypingSpeed 30ms

Type "./target/debug/workhorse --version"
Enter
Sleep 1s
Type "./target/debug/workhorse providers"
Enter
Sleep 3s
Type "GROQ_API_KEY=demo ./target/debug/workhorse doctor"
Enter
Sleep 3s
