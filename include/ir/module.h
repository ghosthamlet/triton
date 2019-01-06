#ifndef TDL_INCLUDE_IR_MODULE_H
#define TDL_INCLUDE_IR_MODULE_H

#include <map>
#include <set>
#include <string>
#include "builder.h"

namespace tdl{
namespace ir{

class basic_block;
class phi_node;
class value;
class context;
class function;
class attribute;
class function_type;
class constant;
class global_value;

/* Module */
class module {
  typedef std::pair<std::string, basic_block*> val_key_t;
  friend class function;

public:
  typedef std::map<std::string, global_value*> symbols_map_t;
  typedef std::vector<function*> functions_list_t;

private:
  phi_node *make_phi(type *ty, unsigned num_values, basic_block *block);
  value *try_remove_trivial_phis(ir::phi_node *&phi);
  value *add_phi_operands(const std::string& name, phi_node *&phi);
  value *get_value_recursive(const std::string& name, basic_block *block);
  void push_function(function *fn) { functions_.push_back(fn); }

public:
  module(const std::string &name, context &ctx);
  context& get_context();
  builder& get_builder();
  // Setters
  void set_value(const std::string& name, basic_block* block, value *x);
  void set_value(const std::string& name, value* x);
  // Getters
  value *get_value(const std::string& name, basic_block* block);
  value *get_value(const std::string& name);
  // Seal block -- no more predecessors will be added
  void seal_block(basic_block *block);
  // Functions
  const functions_list_t &get_function_list() const { return functions_; }
  functions_list_t &get_function_list()             { return functions_; }
  function *get_or_insert_function(const std::string &name, function_type *ty);


private:
  std::string name_;
  context &context_;
  builder builder_;
  std::map<val_key_t, value*> values_;
  std::set<basic_block*> sealed_blocks_;
  std::map<basic_block*, std::map<std::string, phi_node*>> incomplete_phis_;
  functions_list_t functions_;
  symbols_map_t symbols_;
};

}
}

#endif
