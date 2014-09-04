@echo off

{% macro set_error(fail_type='error') -%}
set "BINSTAR_BUILD_RESULT={{fail_type}}" & goto:eof
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
    @echo off

    echo.
    echo [Fetching Build Source]

    rm -rf "%BINSTAR_OWNER%\%BINSTAR_PACKAGE%"
    Mkdir "%BINSTAR_OWNER%"

    {% if git_info %}
        set "GIT_REPO={{git_info['full_name']}}"
        set "GIT_BRANCH={{git_info['branch']}}"
        set "GIT_COMMIT={{git_info['commit']}}"

        rm -rf "%GIT_REPO%"
        Mkdir "%GIT_REPO%"
        echo git clone --recursive --depth=50 --branch=%GIT_BRANCH% https://github.com/%GIT_REPO%.git %GIT_REPO%

        if [ "%GIT_OAUTH_TOKEN%" == "" ]; then
            git clone --recursive --depth=50 --branch="%GIT_BRANCH%" "https://github.com/%GIT_REPO%.git" "%BINSTAR_OWNER%\%BINSTAR_PACKAGE%"  || ( {{set_error()}} )
        else
            git clone --recursive --depth=50 --branch="%GIT_BRANCH%" "https://%GIT_OAUTH_TOKEN%:x-oauth-basic@github.com/%GIT_REPO%.git" "%BINSTAR_OWNER%\%BINSTAR_PACKAGE%"  || ( {{set_error()}} )
        fi
        
        cd "%GIT_REPO%"

        echo "git checkout --quiet %GIT_COMMIT%"
        git checkout --quiet "%GIT_COMMIT%"  || ( {{set_error()}} )

        :: Remove the oath token or (this would be a security violation)
        git remote rm origin  || ( {{set_error()}} )

    {% else %}

        Mkdir "%BINSTAR_OWNER%\%BINSTAR_PACKAGE%"
        cd "%BINSTAR_OWNER%\%BINSTAR_PACKAGE%"
        echo ls  -al %BUILD_TARBALL%
        ls  %BUILD_TARBALL%
        echo "Extracting Package"
        echo tar jxf %BUILD_TARBALL%

        :: tar jxf "%BUILD_TARBALL%" || {{set_error()}}
        python -c "import tarfile; tarfile.open(r'%BUILD_TARBALL%', 'r|bz2').extractall()"

    {% endif %}

    {% if sub_dir %}

    echo Chaning into sub directory of git repository
    echo cd {{sub_dir}}
    cd "{{sub_dir}}" || ( {{set_error()}} )
    
    {% endif %}



    @echo off

goto:eof

:setup_build

    echo|set /p "noNewline=Host: "
    hostname
    echo [Setting engine]
    echo conda create -p "%BUILD_ENV_PATH%" --quiet --yes %BINSTAR_ENGINE%
    rm -rf "%BUILD_ENV_PATH%"
    call conda create -p "%BUILD_ENV_PATH%" --quiet --yes %BINSTAR_ENGINE%
    
    :: Hack to build with the python set in BINSTAR_ENGINE
    python -c "import sys; sys.stdout.write('%%s%%s' %% (sys.version_info.major, sys.version_info.minor))" > %TEMP%\CONDA_PY 
 
    set /p CONDA_PY=<%TEMP%\CONDA_PY 
    echo activate %BUILD_ENV_PATH%

    :: activate does not work within this batch file
    call activate %BUILD_ENV_PATH%
    :: set "CONDA_DEFAULT_ENV=%BUILD_ENV_PATH%"
    :: set "PATH=%BUILD_ENV_PATH%;%BUILD_ENV_PATH%\Scripts;%PATH%"


goto:eof

:: #### #### #### #### #### #### #### #### #### #### #### #### #### #### 
:: User defined build commands
:: #### #### #### #### #### #### #### #### #### #### #### #### #### #### 
{% macro format_instructions(key, fail_type='error') -%}

:bb_{{key}}
    @echo off
    {% set all_instruction_lines = get_list(instructions, key) -%}
    {%- if not all_instruction_lines %}
    :: Empty set of instructions for {{key}}
    {% else -%}

    echo.
    echo [{{key.title().replace('_',' ')}}]
    
    {%   for instruction_lines in all_instruction_lines -%}

    {%      for instruction_line in instruction_lines.split('\n') %}
    echo {{instruction_line}}
    {%      endfor %}

    ( {{instruction_lines}} ) || ( {{set_error(fail_type)}} )
    {%   endfor -%}

    @echo off

    {%- endif %}

goto:eof

{% endmacro %}

{%macro check_result() -%}
if not "%BINSTAR_BUILD_RESULT%" == "" (goto:eof)
{%- endmacro %}

{{ format_instructions('install') }}
{{ format_instructions('test', 'failure') }}
{{ format_instructions('before_script') }}
{{ format_instructions('script', 'failure') }}

{{ format_instructions('after_success') }}
{{ format_instructions('after_error') }}
{{ format_instructions('after_failure') }}
{{ format_instructions('after_script') }}

:binstar_build

    call:bb_install
    {{check_result()}}

    call:bb_test
    {{check_result()}}

    call:bb_before_script
    {{check_result()}}

    call:bb_script
    {{check_result()}}

    set "BINSTAR_BUILD_RESULT=success"

goto:eof


:binstar_post_build
    
    if "%BINSTAR_BUILD_RESULT%" == "success" (
        call:bb_after_success
    )
    if "%BINSTAR_BUILD_RESULT%" == "error" (
        call:bb_after_error
    )
    if "%BINSTAR_BUILD_RESULT%" == "failure" (
        call:bb_after_failure
    )

    call:bb_after_script

goto:eof


:upload_build_targets
    if not "%BINSTAR_BUILD_RESULT%" == "success" (
        goto:eof
    )

    {% if test_only %}

    echo.
    echo Running Build in "Test Only" mode, not uploading build targets

    {% else %}

    call deactivate

    echo .
    echo [Build Targets]
    
    {% for tgt in files %}
    echo binstar -q -t %%TOKEN%% upload --force --user %BINSTAR_OWNER% --package %BINSTAR_PACKAGE% {{channels}} {{tgt}} --build-id %BINSTAR_BUILD_MAJOR%
    binstar -q -t "%BINSTAR_API_TOKEN%" upload --force --user "%BINSTAR_OWNER%" --package "%BINSTAR_PACKAGE%" {{channels}} {{tgt}} --build-id "%BINSTAR_BUILD%" || ( {{ set_error() }} )
    {% else %}
    echo No build targets specified
    {% endfor %}
    {% endif %}


goto:eof

