// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from midterm_msgs:msg/WallList.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "midterm_msgs/msg/detail/wall_list__rosidl_typesupport_introspection_c.h"
#include "midterm_msgs/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "midterm_msgs/msg/detail/wall_list__functions.h"
#include "midterm_msgs/msg/detail/wall_list__struct.h"


// Include directives for member types
// Member `walls`
#include "midterm_msgs/msg/wall.h"
// Member `walls`
#include "midterm_msgs/msg/detail/wall__rosidl_typesupport_introspection_c.h"

#ifdef __cplusplus
extern "C"
{
#endif

void midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__WallList_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  midterm_msgs__msg__WallList__init(message_memory);
}

void midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__WallList_fini_function(void * message_memory)
{
  midterm_msgs__msg__WallList__fini(message_memory);
}

size_t midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__size_function__WallList__walls(
  const void * untyped_member)
{
  const midterm_msgs__msg__Wall__Sequence * member =
    (const midterm_msgs__msg__Wall__Sequence *)(untyped_member);
  return member->size;
}

const void * midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__get_const_function__WallList__walls(
  const void * untyped_member, size_t index)
{
  const midterm_msgs__msg__Wall__Sequence * member =
    (const midterm_msgs__msg__Wall__Sequence *)(untyped_member);
  return &member->data[index];
}

void * midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__get_function__WallList__walls(
  void * untyped_member, size_t index)
{
  midterm_msgs__msg__Wall__Sequence * member =
    (midterm_msgs__msg__Wall__Sequence *)(untyped_member);
  return &member->data[index];
}

void midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__fetch_function__WallList__walls(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const midterm_msgs__msg__Wall * item =
    ((const midterm_msgs__msg__Wall *)
    midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__get_const_function__WallList__walls(untyped_member, index));
  midterm_msgs__msg__Wall * value =
    (midterm_msgs__msg__Wall *)(untyped_value);
  *value = *item;
}

void midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__assign_function__WallList__walls(
  void * untyped_member, size_t index, const void * untyped_value)
{
  midterm_msgs__msg__Wall * item =
    ((midterm_msgs__msg__Wall *)
    midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__get_function__WallList__walls(untyped_member, index));
  const midterm_msgs__msg__Wall * value =
    (const midterm_msgs__msg__Wall *)(untyped_value);
  *item = *value;
}

bool midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__resize_function__WallList__walls(
  void * untyped_member, size_t size)
{
  midterm_msgs__msg__Wall__Sequence * member =
    (midterm_msgs__msg__Wall__Sequence *)(untyped_member);
  midterm_msgs__msg__Wall__Sequence__fini(member);
  return midterm_msgs__msg__Wall__Sequence__init(member, size);
}

static rosidl_typesupport_introspection_c__MessageMember midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__WallList_message_member_array[1] = {
  {
    "walls",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(midterm_msgs__msg__WallList, walls),  // bytes offset in struct
    NULL,  // default value
    midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__size_function__WallList__walls,  // size() function pointer
    midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__get_const_function__WallList__walls,  // get_const(index) function pointer
    midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__get_function__WallList__walls,  // get(index) function pointer
    midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__fetch_function__WallList__walls,  // fetch(index, &value) function pointer
    midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__assign_function__WallList__walls,  // assign(index, value) function pointer
    midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__resize_function__WallList__walls  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__WallList_message_members = {
  "midterm_msgs__msg",  // message namespace
  "WallList",  // message name
  1,  // number of fields
  sizeof(midterm_msgs__msg__WallList),
  midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__WallList_message_member_array,  // message members
  midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__WallList_init_function,  // function to initialize message memory (memory has to be allocated)
  midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__WallList_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__WallList_message_type_support_handle = {
  0,
  &midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__WallList_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_midterm_msgs
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, midterm_msgs, msg, WallList)() {
  midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__WallList_message_member_array[0].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, midterm_msgs, msg, Wall)();
  if (!midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__WallList_message_type_support_handle.typesupport_identifier) {
    midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__WallList_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &midterm_msgs__msg__WallList__rosidl_typesupport_introspection_c__WallList_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif
