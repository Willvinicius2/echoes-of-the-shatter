# RF-51: grava um save com o próprio core (teste save_rf51_sample_for_python_validator) e roda o
# validador de esquema e de regras semânticas do Data Engineer (tools/validate_data.py) sobre ele.
# Uso: cmake -DTEST_BIN=... -DPYTHON=... -DREPO=... -DOUT=<base sem .json> -P run_save_validator.cmake
file(REMOVE_RECURSE "${OUT}.json" "${OUT}.tmp")
set(ENV{SHATTER_SAVE_SAMPLE_OUT} "${OUT}")
execute_process(COMMAND "${TEST_BIN}" save_rf51_sample_for_python_validator RESULT_VARIABLE rc)
if(NOT rc EQUAL 0)
  message(FATAL_ERROR "o core não gravou o save de exemplo (código ${rc})")
endif()
execute_process(COMMAND "${PYTHON}" "${REPO}/tools/validate_data.py"
                        --save "${OUT}.json"
                        --content "${REPO}/ShatterCore/tests/data/rich"
                RESULT_VARIABLE rc)
if(NOT rc EQUAL 0)
  message(FATAL_ERROR "tools/validate_data.py recusou o save gravado pelo core (código ${rc})")
endif()
