# Dev Rules                                                                                                      
1. No emojis in code or output                                                                
2. Write simple, concise code                                                                  
3. No shortcuts, mocks, fallbacks, or stubs — real implementations only
4. Search the web when stuck
5. all code should be hosted on the server directly and the docker should mount the folder for access to the code and data
6. never store files or edit them inside a container and All code should run in a docker
7. use git for each update
   plan the development first
     ensure you understand the notes.md and .md related to the issue
     read the code fully
     develop a plan
     document and open the issue
     then develop, rebuild, test
       write in the issue what youare goign to try, and the results - this should log your progress and provide detail necessary to reconstruct teh logical and techincal work independent of the code and provide for detailed lessons learned
     update .md/notes if needed
     don't use co-authored by claude in the commit messages
     commit push close the issue
8. don't set artifical limits (e.g. docker cpu cores) unless there is a specific requirment
9. if you have not fully read the notes.md recently, do that first!
10. Main CLAIRE-DirectLLM repo is at /Users/joel/02-github/CLAIRE-DirectLLM — do NOT modify any files in that directory. Read-only reference; copy what you need into this repo.
11. GitHub repo: https://github.com/jkirc001/CLAIRE-DirectLLM-Docker
12. Commit SHA to pin: 375a60e3c85a354e754a700d97f53877b00a2515
13. See docker-plan.md for the full implementation plan (Sections 1-6)
