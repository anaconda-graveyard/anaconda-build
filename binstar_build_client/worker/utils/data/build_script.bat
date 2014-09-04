@echo off

{% macro set_error() -%}
set "BINSTAR_BUILD_RESULT=error" & goto:eof
{%- endmacro %}

{% for key, value in exports %}
set {{key}}={{value}}
{% endfor %}


call:parse_options %*
call:main
goto:eof

:: #######################################################
:: Functions
:: #######################################################

:parse_options

  echo parse_options

  :parse_options_loop
    IF NOT "%1"=="" (

        IF "%1"=="--git-oauth-token" (
            SHIFT
            set GIT_OAUTH_TOKEN=%2
            SHIFT
            goto:parse_options_loop
        )

        IF "%1"=="--build-tarball" (
            SHIFT
            set BUILD_TARBALL=%2
            SHIFT
            goto:parse_options_loop
        )

        IF "%1"=="--api-token" (
            SHIFT
            set "BINSTAR_API_TOKEN=%2"
            SHIFT
            goto:parse_options_loop
        )

        echo "Unknown option %1"
        exit /B 11
        
    )


goto:eof

:main

    :: echo GIT_OAUTH_TOKEN=%GIT_OAUTH_TOKEN%
    :: echo BUILD_TARBALL=%BUILD_TARBALL%
    :: echo BINSTAR_API_TOKEN=%BINSTAR_API_TOKEN%

    set BINSTAR_BUILD_RESULT=
    echo setup_build

    :: call:setup_build;

    if not "%BINSTAR_BUILD_RESULT%" == "" (
        echo Internal binstar build error: Could not set up initial build state
        exit /B 9
    )

    echo fetch_build_source
    call:fetch_build_source

    if not "%BINSTAR_BUILD_RESULT%" == "" (
        echo %BINSTAR_BUILD_RESULT% Binstar build error: Could not fetch build sources
        exit /B 11
    )

    call:binstar_build
    call:binstar_post_build

    call:upload_build_targets

    echo Exit BINSTAR_BUILD_RESULT="%BINSTAR_BUILD_RESULT%"

    if "%BINSTAR_BUILD_RESULT%" == "success" (
        exit /B 0
    )
    if "%BINSTAR_BUILD_RESULT%" == "error" (
        exit /B 11
    )

    if "%BINSTAR_BUILD_RESULT%" == "failure" (
        exit /B 12
    )
    
    exit /B 13


goto:eof

:: #######################################################

:fetch_build_source
    @echo on
    echo.
    echo [Fetching Build Source]

    rm -rf "%BINSTAR_OWNER%\%BINSTAR_PACKAGE%"
    Mkdir "%BINSTAR_OWNER%\%BINSTAR_PACKAGE%"
    cd "%BINSTAR_OWNER%\%BINSTAR_PACKAGE%"



    {% if git_info %}
        set "GIT_REPO={{git_info['full_name']}}"
        set "GIT_BRANCH={{git_info['branch']}}"
        set "GIT_COMMIT={{git_info['commit']}}"

        rm -rf "%GIT_REPO%"
        Mkdir "%GIT_REPO%"
        echo git clone --recursive --depth=50 --branch=$GIT_BRANCH https://github.com/${GIT_REPO}.git %GIT_REPO%

        if [ "%GIT_OAUTH_TOKEN%" == "" ]; then
            git clone --recursive --depth=50 --branch="$GIT_BRANCH" "https://github.com/${GIT_REPO}.git" "%GIT_REPO%"
                eval $bb_check_command_error
        else
            git clone --recursive --depth=50 --branch="$GIT_BRANCH" "https://%GIT_OAUTH_TOKEN%:x-oauth-basic@github.com/${GIT_REPO}.git" "%GIT_REPO%"
                eval $bb_check_command_error
        fi
        
        cd "%GIT_REPO%"

        echo "git checkout --quiet $GIT_COMMIT"
        git checkout --quiet "$GIT_COMMIT"
            eval $bb_check_command_error
        # Remove the oath token or (this would be a security violation)
        git remote rm origin
            eval $bb_check_command_error

        {% if sub_dir %}
        echo "Chaning into sub directory of git repository"
        echo "cd {{sub_dir}}"
        cd "{{sub_dir}}"
        eval $bb_check_command_error
        {% endif %}


    {% else %}

        echo ls  -al %BUILD_TARBALL%
        ls  %BUILD_TARBALL%
        echo "Extracting Package"
        echo tar jxf %BUILD_TARBALL%

        :: tar jxf "%BUILD_TARBALL%" || {{set_error()}}
        python -c "import tarfile; tarfile.open(r'%BUILD_TARBALL%', 'r|bz2').extractall()"


    {% endif %}



    @echo off

goto:eof

:setup_build

    echo|set /p "noNewline=Host: "
    hostname
    echo Setting engine
    echo conda create -p "%BUILD_ENV_PATH%" --quiet --yes %BINSTAR_ENGINE%

    :: @echo on

    rm -rf "%BUILD_ENV_PATH%"


    echo BEFORE CALL CONDA CREATE
    call conda create -p "%BUILD_ENV_PATH%" --quiet --yes %BINSTAR_ENGINE%
    echo AFTER CALL CONDA CREATE
    
    :: Hack to build with the python set in BINSTAR_ENGINE
    python -c "import sys; sys.stdout.write('%%s%%s' %% (sys.version_info.major, sys.version_info.minor))" > %TEMP%\CONDA_PY 
 
    set /p CONDA_PY=<%TEMP%\CONDA_PY 
    echo activate %BUILD_ENV_PATH%

    :: activate does not work within this batch file
    :: activate %BUILD_ENV_PATH%
    set "CONDA_DEFAULT_ENV=%BUILD_ENV_PATH%"
    set "PATH=%BUILD_ENV_PATH%;%BUILD_ENV_PATH%\Scripts;%PATH%"


goto:eof


:binstar_build
    echo binstar_build
    set "BINSTAR_BUILD_RESULT=success"

goto:eof


:binstar_post_build
    
    echo binstar_post_build

goto:eof


:upload_build_targets

    echo upload_build_targets

goto:eof


:handle_error

    echo "handle_error"

goto:eof
